import {
  type AggregationOutputType,
  type DataUnit,
  DurationUnit,
  RateUnit,
  SizeUnit,
} from 'sentry/utils/discover/fields';

export const Y_AXIS_INTEGER_TOLERANCE = 0.000001;
export const FALLBACK_TYPE = 'number';
export const FALLBACK_UNIT_FOR_FIELD_TYPE = {
  number: null,
  integer: null,
  date: null,
  duration: DurationUnit.MILLISECOND,
  percentage: null,
  string: null,
  size: SizeUnit.BYTE,
  rate: RateUnit.PER_SECOND,
} satisfies Record<AggregationOutputType, DataUnit>;
