import {Component, Fragment} from 'react';
import styled from '@emotion/styled';

import {Select} from 'sentry/components/core/select';
import FieldGroup from 'sentry/components/forms/fieldGroup';
import {
  AlertRuleSensitivity,
  AlertRuleThresholdType,
  type UnsavedMetricRule,
} from 'sentry/views/alerts/rules/metric/types';

type Props = {
  disabled: boolean;
  onSensitivityChange: (sensitivity: AlertRuleSensitivity) => void;
  onThresholdTypeChange: (thresholdType: AlertRuleThresholdType) => void;
  sensitivity: UnsavedMetricRule['sensitivity'];
  thresholdType: UnsavedMetricRule['thresholdType'];
  /**
   * Map of fieldName -> errorMessage
   */
  error?: Record<string, string>;

  hideControl?: boolean;
};

type SensitivityFormItemProps = {
  onSensitivityChange: (sensitivity: AlertRuleSensitivity) => void;
  sensitivity: UnsavedMetricRule['sensitivity'];
};

type DirectionFormItemProps = {
  onThresholdTypeChange: (thresholdType: AlertRuleThresholdType) => void;
  thresholdType: UnsavedMetricRule['thresholdType'];
};

function SensitivityFormItem({
  sensitivity,
  onSensitivityChange,
}: SensitivityFormItemProps) {
  return (
    <StyledField
      label={'Level of responsiveness'}
      id={'sensitivity'}
      help={
        'Choose your level of anomaly responsiveness. Higher thresholds means alerts for most anomalies. Lower thresholds means alerts only for larger ones.'
      }
      required
    >
      <SelectContainer>
        <Select
          name="sensitivity"
          inputId={'sensitivity'}
          value={sensitivity}
          options={[
            {
              value: AlertRuleSensitivity.LOW,
              label: 'Low (alert less often)',
            },
            {
              value: AlertRuleSensitivity.MEDIUM,
              label: 'Medium',
            },
            {
              value: AlertRuleSensitivity.HIGH,
              label: 'High (alert more often)',
            },
          ]}
          onChange={({value}: any) => {
            onSensitivityChange(value);
          }}
        />
      </SelectContainer>
    </StyledField>
  );
}

function DirectionFormItem({
  thresholdType,
  onThresholdTypeChange,
}: DirectionFormItemProps) {
  return (
    <StyledField
      label={'Direction of anomaly movement'}
      help={
        'Decide if you want to be alerted to anomalies that are moving above, below, or in both directions in relation to your threshold.'
      }
      required
    >
      <SelectContainer>
        <Select
          name="sensitivity"
          value={thresholdType}
          options={[
            {
              value: AlertRuleThresholdType.ABOVE_AND_BELOW,
              label: 'Above and below bounds',
            },
            {
              value: AlertRuleThresholdType.ABOVE,
              label: 'Above bounds only',
            },
            {
              value: AlertRuleThresholdType.BELOW,
              label: 'Below bounds only',
            },
          ]}
          onChange={({value}: any) => {
            onThresholdTypeChange(value);
          }}
        />
      </SelectContainer>
    </StyledField>
  );
}

class AnomalyDetectionFormField extends Component<Props> {
  render() {
    const {sensitivity, onSensitivityChange, thresholdType, onThresholdTypeChange} =
      this.props;

    return (
      <Fragment>
        <SensitivityFormItem
          sensitivity={sensitivity}
          onSensitivityChange={onSensitivityChange}
        />
        <DirectionFormItem
          thresholdType={thresholdType}
          onThresholdTypeChange={onThresholdTypeChange}
        />
      </Fragment>
    );
  }
}

const StyledField = styled(FieldGroup)`
  & > label > div:first-child > span {
    display: flex;
    flex-direction: row;
  }
`;

const SelectContainer = styled('div')`
  flex: 1;
`;
export default AnomalyDetectionFormField;
