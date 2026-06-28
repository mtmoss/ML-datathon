"""Testes do contrato de dados (Dia 0: garante que o repo roda e o CI fica verde)."""

from datathon_offerexp.contracts import DecisionRecord, SyntheticOfferEvent


def test_cria_evento_oferta() -> None:
    evento = SyntheticOfferEvent(
        event_id="evt_001",
        occurred_at="2026-07-01T10:00:00Z",
        subject_key="sub_001",
        channel="app",
        segment="novo",
        available_arms=("sem_oferta", "educacao_financeira"),
    )
    assert evento.chosen_arm is None
    assert "educacao_financeira" in evento.available_arms


def test_baseline_escolhe_primeiro_braco() -> None:
    from datathon_offerexp.policies import baseline_select

    evento = SyntheticOfferEvent(
        event_id="evt_002",
        occurred_at="2026-07-01T10:05:00Z",
        subject_key="sub_002",
        channel="web",
        segment="recorrente",
        available_arms=("simulador_credito", "sem_oferta"),
    )
    assert baseline_select(evento) == "simulador_credito"


def test_decision_record() -> None:
    rec = DecisionRecord(
        decision_id="dec_001",
        event_id="evt_001",
        policy_version="policy-demo-v0",
        selected_arm="educacao_financeira",
        mode="adaptive",
        exploration=False,
        reason_codes=("elegivel", "maior_score"),
        created_at="2026-07-01T10:00:01Z",
    )
    assert rec.selected_arm == "educacao_financeira"
