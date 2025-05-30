import {EventFixture} from 'sentry-fixture/event';

import {initializeOrg} from 'sentry-test/initializeOrg';
import {render, screen, userEvent} from 'sentry-test/reactTestingLibrary';
import {textWithMarkupMatcher} from 'sentry-test/utils';

import {EventTags} from 'sentry/components/events/eventTags';

describe('event tags', function () {
  const {organization, project} = initializeOrg({
    organization: {
      relayPiiConfig: null,
    },
  });

  it('display redacted tags', async function () {
    const event = EventFixture({
      tags: null,
      _meta: {
        tags: {'': {rem: [['project:2', 'x']]}},
      },
    });

    render(<EventTags projectSlug={project.slug} event={event} />, {organization});

    await userEvent.hover(screen.getByText(/redacted/));
    expect(
      await screen.findByText(
        textWithMarkupMatcher(
          "Removed because of a data scrubbing rule in your project's settings"
        )
      ) // Fall back case
    ).toBeInTheDocument(); // tooltip description
  });

  it('display redacted "app.device" tag', async function () {
    const tags = [
      {key: 'app.device', value: null},
      {key: 'device.family', value: 'iOS'},
    ];

    const event = EventFixture({
      tags,
      _meta: {
        tags: {
          '0': {
            value: {
              '': {rem: [['project:2', 'x']]},
            },
          },
        },
      },
    });

    MockApiClient.addMockResponse({
      url: `/projects/${organization.slug}/${project.slug}/`,
      body: project,
    });

    render(<EventTags projectSlug={project.slug} event={event} />, {organization});
    expect(await screen.findByTestId('loading-indicator')).not.toBeInTheDocument();

    expect(screen.getByText('device.family')).toBeInTheDocument();
    expect(screen.getByText('iOS')).toBeInTheDocument();

    expect(screen.getByText('app.device')).toBeInTheDocument();
    await userEvent.hover(screen.getByText(/redacted/));

    expect(
      await screen.findByText(
        textWithMarkupMatcher(
          "Removed because of a data scrubbing rule in your project's settings"
        )
      ) // Fall back case
    ).toBeInTheDocument(); // tooltip description
  });

  it('transaction tag links to transaction overview', async function () {
    const tags = [{key: 'transaction', value: 'mytransaction'}];

    const event = EventFixture({
      tags,
    });

    MockApiClient.addMockResponse({
      url: `/projects/${organization.slug}/${project.slug}/`,
      body: project,
    });

    render(<EventTags projectSlug={project.slug} event={event} />, {organization});
    expect(await screen.findByTestId('loading-indicator')).not.toBeInTheDocument();

    expect(screen.getByText('mytransaction')).toBeInTheDocument();
    expect(screen.getByRole('link')).toHaveAttribute(
      'href',
      `/organizations/${organization.slug}/insights/summary/?project=1&referrer=event-tags-table&transaction=mytransaction`
    );
  });
});
