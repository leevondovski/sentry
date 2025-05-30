import styled from '@emotion/styled';

import type {SpanType} from 'sentry/components/events/interfaces/spans/types';
import Link from 'sentry/components/links/link';
import {IconGraph} from 'sentry/icons/iconGraph';
import {t} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import type {EventTransaction} from 'sentry/types/event';
import type {Organization} from 'sentry/types/organization';
import {trackAnalytics} from 'sentry/utils/analytics';
import {useLocation} from 'sentry/utils/useLocation';
import {resolveSpanModule} from 'sentry/views/insights/common/utils/resolveSpanModule';
import {useModuleURL} from 'sentry/views/insights/common/utils/useModuleURL';
import {ModuleName} from 'sentry/views/insights/types';
import {
  querySummaryRouteWithQuery,
  resourceSummaryRouteWithQuery,
} from 'sentry/views/performance/transactionSummary/transactionSpans/spanDetails/utils';

interface Props {
  event: Readonly<EventTransaction>;
  organization: Organization;
  span: SpanType;
}

function SpanSummaryLink(props: Props) {
  const location = useLocation();
  const resourceBaseUrl = useModuleURL(ModuleName.RESOURCE);
  const queryBaseUrl = useModuleURL(ModuleName.DB);

  const {event, organization, span} = props;

  const sentryTags = span.sentry_tags;
  if (!sentryTags?.group) {
    return null;
  }

  const resolvedModule = resolveSpanModule(sentryTags.op, sentryTags.category);

  if (
    organization.features.includes('insights-initial-modules') &&
    resolvedModule === ModuleName.DB
  ) {
    return (
      <Link
        to={querySummaryRouteWithQuery({
          base: queryBaseUrl,
          query: location.query,
          group: sentryTags.group,
          projectID: event.projectID,
        })}
        onClick={() => {
          trackAnalytics('trace.trace_layout.view_in_insight_module', {
            organization,
            module: ModuleName.DB,
          });
        }}
      >
        <StyledIconGraph type="area" size="xs" />
        {t('View Summary')}
      </Link>
    );
  }

  if (
    organization.features.includes('insights-initial-modules') &&
    resolvedModule === ModuleName.RESOURCE &&
    resourceSummaryAvailable(sentryTags.op)
  ) {
    return (
      <Link
        to={resourceSummaryRouteWithQuery({
          baseUrl: resourceBaseUrl,
          query: location.query,
          group: sentryTags.group,
          projectID: event.projectID,
        })}
        onClick={() => {
          trackAnalytics('trace.trace_layout.view_in_insight_module', {
            organization,
            module: ModuleName.RESOURCE,
          });
        }}
      >
        <StyledIconGraph size="xs" />
        {t('View Summary')}
      </Link>
    );
  }

  return null;
}

const StyledIconGraph = styled(IconGraph)`
  margin-right: ${space(0.5)};
`;

const resourceSummaryAvailable = (op = '') =>
  ['resource.script', 'resource.css'].includes(op);

export default SpanSummaryLink;
