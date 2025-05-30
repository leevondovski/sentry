import {Component} from 'react';
import * as Sentry from '@sentry/react';
import isEqual from 'lodash/isEqual';

import type {ResponseMeta} from 'sentry/api';
import {Client} from 'sentry/api';
import LoadingError from 'sentry/components/loadingError';
import LoadingIndicator from 'sentry/components/loadingIndicator';
import {t} from 'sentry/locale';
import type {
  RouteComponentProps,
  RouteContextInterface,
} from 'sentry/types/legacyReactRouter';
import PermissionDenied from 'sentry/views/permissionDenied';
import RouteError from 'sentry/views/routeError';

export interface AsyncComponentProps extends Partial<RouteComponentProps> {}

export interface AsyncComponentState {
  [key: string]: any;
  error: boolean;
  errors: Record<string, ResponseMeta>;
  loading: boolean;
  reloading: boolean;
  remainingRequests?: number;
}

/**
 * Wraps methods on the AsyncComponent to catch errors and set the `error`
 * state on error.
 */
function wrapErrorHandling<T extends any[], U>(
  component: DeprecatedAsyncComponent,
  fn: (...args: T) => U
) {
  return (...args: T): U | null => {
    try {
      return fn(...args);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(error);
      window.setTimeout(() => {
        throw error;
      });
      component.setState({error});
      return null;
    }
  };
}

/**
 * @deprecated use useApiQuery instead
 *
 * Read the dev docs page on network requests for more information [1].
 *
 * [1]: https://develop.sentry.dev/frontend/network-requests/
 */
class DeprecatedAsyncComponent<
  P extends AsyncComponentProps = AsyncComponentProps,
  S extends AsyncComponentState = AsyncComponentState,
> extends Component<P, S> {
  constructor(props: P) {
    super(props);

    this.api = new Client();
    this.fetchData = wrapErrorHandling(this, this.fetchData.bind(this));
    this.render = wrapErrorHandling(this, this.render.bind(this));

    this.state = this.getDefaultState() as Readonly<S>;
  }

  componentDidMount() {
    this.fetchData();

    if (this.reloadOnVisible) {
      document.addEventListener('visibilitychange', this.visibilityReloader);
    }
  }

  componentDidUpdate(prevProps: P, _prevState: S) {
    const isLocationInProps = prevProps.location !== undefined;

    const currentLocation = isLocationInProps ? this.props.location : null;
    const prevLocation = isLocationInProps ? prevProps.location : null;

    if (!(currentLocation && prevLocation)) {
      return;
    }

    // Re-fetch data when router params change.
    if (
      !isEqual(this.props.params, prevProps.params) ||
      currentLocation.search !== prevLocation.search ||
      currentLocation.state !== prevLocation.state
    ) {
      this.remountComponent();
    }
  }

  componentWillUnmount() {
    this.api.clear();
    document.removeEventListener('visibilitychange', this.visibilityReloader);
  }

  declare context: {router: RouteContextInterface};

  /**
   * Override this flag to have the component reload its state when the window
   * becomes visible again. This will set the loading and reloading state, but
   * will not render a loading state during reloading.
   *
   * eslint-disable-next-line react/sort-comp
   */
  reloadOnVisible = false;

  /**
   * When enabling reloadOnVisible, this flag may be used to turn on and off
   * the reloading. This is useful if your component only needs to reload when
   * becoming visible during certain states.
   *
   * eslint-disable-next-line react/sort-comp
   */
  shouldReloadOnVisible = false;

  /**
   * This affects how the component behaves when `remountComponent` is called
   * By default, the component gets put back into a "loading" state when re-fetching data.
   * If this is true, then when we fetch data, the original ready component remains mounted
   * and it will need to handle any additional "reloading" states
   */
  shouldReload = false;

  /**
   * should `renderError` render the `detail` attribute of a 400 error
   */
  shouldRenderBadRequests = false;

  /**
   * If a request fails and is not a bad request, and if `disableErrorReport` is set to false,
   * the UI will display an error modal.
   *
   * It is recommended to enable this property ideally only when the subclass is used by a top level route.
   */
  disableErrorReport = true;

  api: Client = new Client();

  // XXX: can't call this getInitialState as React whines
  getDefaultState(): AsyncComponentState {
    const endpoints = this.getEndpoints();

    const state = {
      // has all data finished requesting?
      loading: true,
      // is the component reload
      reloading: false,
      // is there an error loading ANY data?
      error: false,
      errors: {},
      // We will fetch immeditaely upon mount
      remainingRequests: endpoints.length || undefined,
    };

    // We are not loading if there are no endpoints
    if (!endpoints.length) {
      state.loading = false;
    }

    endpoints.forEach(([stateKey, _endpoint]) => {
      // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
      state[stateKey] = null;
    });
    return state;
  }

  remountComponent = () => {
    if (this.shouldReload) {
      this.reloadData();
    } else {
      this.setState(this.getDefaultState(), this.fetchData);
    }
  };

  visibilityReloader = () =>
    this.shouldReloadOnVisible &&
    !this.state.loading &&
    !document.hidden &&
    this.reloadData();

  reloadData() {
    this.fetchData({reloading: true});
  }

  fetchData = (extraState?: Record<PropertyKey, unknown>) => {
    const endpoints = this.getEndpoints();

    if (!endpoints.length) {
      this.setState({loading: false, error: false});
      return;
    }

    // Cancel any in flight requests
    this.api.clear();

    this.setState({
      loading: true,
      error: false,
      remainingRequests: endpoints.length,
      ...extraState,
    });

    endpoints.forEach(([stateKey, endpoint, params, options]) => {
      options = options || {};
      // If you're using nested async components/views make sure to pass the
      // props through so that the child component has access to props.location
      const locationQuery = this.props.location?.query || {};
      let query = params?.query || {};
      // If paginate option then pass entire `query` object to API call
      // It should only be expecting `query.cursor` for pagination
      if ((options.paginate || locationQuery.cursor) && !options.disableEntireQuery) {
        query = {...locationQuery, ...query};
      }

      this.api.request(endpoint, {
        method: 'GET',
        ...params,
        query,
        success: (data, _, resp) => {
          this.handleRequestSuccess({stateKey, data, resp}, true);
        },
        error: error => {
          // Allow endpoints to fail
          // allowError can have side effects to handle the error
          if (options.allowError?.(error)) {
            error = null;
          }
          this.handleError(error, [stateKey, endpoint, params, options]);
        },
      });
    });
  };

  onRequestSuccess(_resp: any /* {stateKey, data, resp} */) {
    // Allow children to implement this
  }

  onRequestError(_resp: any, _args: any) {
    // Allow children to implement this
  }

  onLoadAllEndpointsSuccess() {
    // Allow children to implement this
  }

  handleRequestSuccess({stateKey, data, resp}: any, initialRequest?: boolean) {
    this.setState(
      prevState => {
        const state = {
          [stateKey]: data,
          // TODO(billy): This currently fails if this request is retried by SudoModal
          [`${stateKey}PageLinks`]: resp?.getResponseHeader('Link'),
        };

        if (initialRequest) {
          state.remainingRequests = prevState.remainingRequests! - 1;
          state.loading = prevState.remainingRequests! > 1;
          state.reloading = prevState.reloading && state.loading;
        }

        return state;
      },
      () => {
        // if everything is loaded and we don't have an error, call the callback
        if (this.state.remainingRequests === 0 && !this.state.error) {
          this.onLoadAllEndpointsSuccess();
        }
      }
    );
    this.onRequestSuccess({stateKey, data, resp});
  }

  handleError(error: any, args: any) {
    const [stateKey] = args;
    if (error?.responseText) {
      Sentry.addBreadcrumb({
        message: error.responseText,
        category: 'xhr',
        level: 'error',
      });
    }
    this.setState(prevState => {
      const loading = prevState.remainingRequests! > 1;
      const state: AsyncComponentState = {
        [stateKey]: null,
        errors: {
          ...prevState.errors,
          [stateKey]: error,
        },
        error: prevState.error || !!error,
        remainingRequests: prevState.remainingRequests! - 1,
        loading,
        reloading: prevState.reloading && loading,
      };

      return state;
    });
    this.onRequestError(error, args);
  }

  /**
   * Return a list of endpoint queries to make.
   *
   * return [
   *   ['stateKeyName', '/endpoint/', {optional: 'query params'}, {options}]
   * ]
   */
  getEndpoints(): Array<[string, string, any?, any?]> {
    return [];
  }

  renderLoading(): React.ReactNode {
    return <LoadingIndicator />;
  }

  renderError(error?: Error, disableLog = false): React.ReactNode {
    const {errors} = this.state;

    // 401s are captured by SudoModal, but may be passed back to AsyncComponent if they close the modal without identifying
    const unauthorizedErrors = Object.values(errors).find(resp => resp?.status === 401);

    // Look through endpoint results to see if we had any 403s, means their role can not access resource
    const permissionErrors = Object.values(errors).find(resp => resp?.status === 403);

    // If all error responses have status code === 0, then show error message but don't
    // log it to sentry
    const shouldLogSentry =
      Object.values(errors).some(resp => resp?.status !== 0) || disableLog;

    if (unauthorizedErrors) {
      return (
        <LoadingError message={t('You are not authorized to access this resource.')} />
      );
    }

    if (permissionErrors) {
      return <PermissionDenied />;
    }

    if (this.shouldRenderBadRequests) {
      const badRequests = Object.values(errors)
        .filter(resp => resp?.status === 400 && resp?.responseJSON?.detail)
        .map(resp => resp.responseJSON.detail);

      if (badRequests.length) {
        return <LoadingError message={[...new Set(badRequests)].join('\n')} />;
      }
    }

    return (
      <RouteError
        error={error}
        disableLogSentry={!shouldLogSentry}
        disableReport={this.disableErrorReport}
      />
    );
  }

  get shouldRenderLoading() {
    return this.state.loading && (!this.shouldReload || !this.state.reloading);
  }

  renderComponent() {
    return this.shouldRenderLoading
      ? this.renderLoading()
      : this.state.error
        ? this.renderError()
        : this.renderBody();
  }

  /**
   * Renders once all endpoints have been loaded
   */
  renderBody(): React.ReactNode {
    // Allow children to implement this
    throw new Error('Not implemented');
  }

  render() {
    return this.renderComponent();
  }
}

export default DeprecatedAsyncComponent;
