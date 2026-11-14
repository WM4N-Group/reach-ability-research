"""Conditional outer rejection from an optimistic scalar safety-margin envelope."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math


@dataclass(frozen=True)
class ScalarNoGoResult:
    verdict: str
    optimistic_minimum_margin: float
    witness_time_s: float
    contact_authorized: bool = False


def _segment_minimum(margin: Fraction, rate: Fraction, acceleration: Fraction,
                     duration: Fraction) -> tuple[Fraction, Fraction]:
    candidates = [(margin, Fraction(0)),
                  (margin + rate * duration + acceleration * duration**2 / 2, duration)]
    if acceleration > 0:
        stationary = -rate / acceleration
        if 0 < stationary < duration:
            candidates.append((margin + rate * stationary
                               + acceleration * stationary**2 / 2, stationary))
    return min(candidates)


def evaluate_scalar_no_go(
    *,
    margin_upper: float,
    margin_rate_upper: float,
    acceleration_upper_during_delay: float,
    acceleration_upper_after_delay: float,
    control_delay_s: float,
    horizon_s: float,
) -> ScalarNoGoResult:
    """Refute safety if even the most optimistic margin reaches zero.

    Valid only when the caller has externally proved initial upper bounds and
    piecewise upper bounds on the margin's second derivative for every allowed
    control, hidden state and contact mode. The margin rate must be absolutely
    continuous or have only nonpositive jumps. This result concerns the supplied
    scalar margin; mapping its zero crossing to an original termination event
    requires a separate proof. An undetermined result proves nothing.
    """
    values = (margin_upper, margin_rate_upper, acceleration_upper_during_delay,
              acceleration_upper_after_delay, control_delay_s, horizon_s)
    if (not all(math.isfinite(value) for value in values)
            or control_delay_s < 0.0 or horizon_s <= 0.0):
        raise ValueError("Require finite bounds, a nonnegative delay and positive horizon")
    margin, rate, acceleration_d, acceleration_u, control_delay, horizon = (
        Fraction(value) for value in values
    )
    delay = min(control_delay, horizon)
    first_margin, first_time = _segment_minimum(
        margin, rate, acceleration_d, delay,
    )
    margin_at_delay = margin + rate * delay + acceleration_d * delay**2 / 2
    rate_at_delay = rate + acceleration_d * delay
    second_margin, second_time = _segment_minimum(
        margin_at_delay, rate_at_delay, acceleration_u, horizon - delay,
    )
    minimum, witness_time = min((first_margin, first_time),
                                (second_margin, delay + second_time))
    try:
        reported_minimum = float(minimum)
        reported_time = float(witness_time)
    except OverflowError as exc:
        raise ValueError("Optimistic safety envelope overflowed") from exc
    if (not math.isfinite(reported_minimum)
            or (minimum != 0 and reported_minimum == 0.0)):
        raise ValueError("Optimistic safety envelope cannot be reported as a float")
    return ScalarNoGoResult(
        "conditional_unavoidable_violation" if minimum <= 0 else "undetermined",
        reported_minimum, reported_time,
    )
