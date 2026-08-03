"""Gestao de risco: stop-loss/take-profit baseados em ATR e dimensionamento
de posicao (position sizing) por percentual de capital arriscado.

A ideia classica de gestao de risco: nunca arriscar mais que X% do capital
em um unico trade. O stop e colocado a uma distancia (multiplo do ATR) que
respeita a volatilidade real do ativo, em vez de uma % fixa arbitraria.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskPlan:
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_per_unit: float
    position_size: float  # quantidade do ativo (ex: quantos BTC)
    position_value: float  # valor da posicao na moeda de cotacao (ex: USDT)
    risk_amount: float  # quanto capital esta sendo arriscado nesse trade
    risk_reward_ratio: float


def build_risk_plan(
    capital: float,
    entry_price: float,
    atr: float,
    risk_pct: float = 1.0,
    atr_mult_stop: float = 1.5,
    reward_risk_ratio: float = 2.0,
) -> RiskPlan:
    """Monta um plano de risco para uma entrada comprada (long).

    - stop_loss fica `atr_mult_stop * ATR` abaixo da entrada.
    - take_profit fica `reward_risk_ratio` vezes essa distancia acima da entrada.
    - o tamanho da posicao e calculado para que, se o stop for atingido, a
      perda seja exatamente `risk_pct`% do capital informado.
    """
    if capital <= 0:
        raise ValueError("capital deve ser positivo")
    if entry_price <= 0:
        raise ValueError("entry_price deve ser positivo")
    if atr <= 0:
        raise ValueError("ATR invalido (dados insuficientes ou ativo sem volatilidade)")
    if not (0 < risk_pct <= 100):
        raise ValueError("risk_pct deve estar entre 0 e 100")

    stop_distance = atr * atr_mult_stop
    stop_loss = entry_price - stop_distance
    take_profit = entry_price + stop_distance * reward_risk_ratio

    if stop_loss <= 0:
        raise ValueError("Stop-loss calculado ficou <= 0; reduza atr_mult_stop")

    risk_amount = capital * (risk_pct / 100)
    risk_per_unit = entry_price - stop_loss
    position_size = risk_amount / risk_per_unit
    position_value = position_size * entry_price

    # nunca alocar mais do que 100% do capital disponivel, mesmo que o stop
    # seja muito apertado e o calculo por risco peca uma posicao maior.
    if position_value > capital:
        position_size = capital / entry_price
        position_value = capital

    return RiskPlan(
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_per_unit=risk_per_unit,
        position_size=position_size,
        position_value=position_value,
        risk_amount=risk_amount,
        risk_reward_ratio=reward_risk_ratio,
    )
