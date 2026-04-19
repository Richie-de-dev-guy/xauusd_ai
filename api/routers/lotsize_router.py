"""
Lot size router — Step 8: Live Lot Size Calculator.

GET  /api/lotsize           Current pre-calculated lot size from latest bot cycle
POST /api/lotsize/calculate Custom calculation — override any input to run what-ifs

All inputs default to live state values so the dashboard can call POST with
an empty body to reproduce the bot's exact current calculation, or override
individual fields (e.g. risk_pct=2.0) to model scenarios without touching config.
"""

import os
import sys

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.schemas import LotCalcData, LotCalcRequest
from api.state import bot_state

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import config as _config
    _DEFAULT_RISK_PCT      = _config.RISK_PERCENT_PER_TRADE
    _DEFAULT_CONTRACT_SIZE = 100.0   # standard Gold contract; overridden by symbol_info
    _ATR_MULTIPLIER        = 1.5
    _VOLUME_MIN            = 0.01
    _VOLUME_MAX            = 500.0
    _VOLUME_STEP           = 0.01
except Exception:
    _DEFAULT_RISK_PCT      = 1.0
    _DEFAULT_CONTRACT_SIZE = 100.0
    _ATR_MULTIPLIER        = 1.5
    _VOLUME_MIN            = 0.01
    _VOLUME_MAX            = 500.0
    _VOLUME_STEP           = 0.01

router = APIRouter(prefix="/api/lotsize", tags=["lotsize"])


def _calculate(
    balance: float,
    risk_pct: float,
    atr: float,
    spread: float,
    atr_multiplier: float,
    contract_size: float = _DEFAULT_CONTRACT_SIZE,
) -> LotCalcData:
    """Pure calculation — no MT5 calls, fully testable."""
    risk_amount = round(balance * risk_pct / 100, 2)
    sl_distance = round(atr_multiplier * atr + spread, 5)

    if sl_distance > 0 and contract_size > 0:
        raw_lot = risk_amount / (sl_distance * contract_size)
    else:
        raw_lot = _VOLUME_MIN

    # Round to broker volume step
    rounded = max(_VOLUME_MIN, round(raw_lot / _VOLUME_STEP) * _VOLUME_STEP)
    rounded = min(rounded, _VOLUME_MAX)

    return LotCalcData(
        balance=balance,
        risk_pct=risk_pct,
        risk_amount=risk_amount,
        atr=atr,
        spread=spread,
        sl_distance=sl_distance,
        contract_size=contract_size,
        calculated_lot=round(raw_lot, 4),
        rounded_lot=round(rounded, 2),
    )


@router.get("", response_model=LotCalcData)
async def get_live_lotsize(_: str = Depends(get_current_user)) -> LotCalcData:
    """
    Return the lot size the bot calculated on the most recent cycle.
    Uses the pre-computed sl_distance and risk_amount already stored in state.
    """
    s = bot_state.snapshot()

    # Reconstruct a full breakdown from stored state values
    risk_pct = _DEFAULT_RISK_PCT
    balance  = s.balance or 0.0
    atr      = s.atr or 0.0
    spread   = s.spread or 0.0

    return _calculate(
        balance=balance,
        risk_pct=risk_pct,
        atr=atr,
        spread=spread,
        atr_multiplier=_ATR_MULTIPLIER,
    )


@router.post("/calculate", response_model=LotCalcData)
async def calculate_lotsize(
    body: LotCalcRequest,
    _: str = Depends(get_current_user),
) -> LotCalcData:
    """
    Interactive what-if calculator.

    Any field left null falls back to the current live value from state,
    so the frontend can let the user slide a single knob (e.g. risk %)
    while everything else stays anchored to the live bot reading.
    """
    s = bot_state.snapshot()

    balance      = body.balance  if body.balance  is not None else (s.balance or 0.0)
    risk_pct     = body.risk_pct if body.risk_pct is not None else _DEFAULT_RISK_PCT
    atr          = body.atr      if body.atr      is not None else (s.atr or 0.0)
    spread       = body.spread   if body.spread   is not None else (s.spread or 0.0)
    atr_mult     = body.atr_multiplier

    return _calculate(
        balance=balance,
        risk_pct=risk_pct,
        atr=atr,
        spread=spread,
        atr_multiplier=atr_mult,
    )
