"""Testes da camada de enriquecimento sintetico (Etapa 2)."""

from datathon_offerexp import synthetic as syn


def test_catalogo_tem_todos_os_bracos() -> None:
    cat = syn.build_catalog()
    assert set(cat["arm_id"]) == set(syn.ARMS)


def test_true_conv_prob_no_intervalo() -> None:
    p = syn.true_conv_prob(0.2, "oferta_deposito", "reativado", "app")
    assert 0.0 <= p <= 0.95


def test_oferta_direta_irrita_cliente_novo() -> None:
    # mesma propensao base: cliente novo converte menos com oferta direta
    novo = syn.true_conv_prob(0.2, "oferta_deposito", "novo", "web")
    reativado = syn.true_conv_prob(0.2, "oferta_deposito", "reativado", "web")
    assert novo < reativado


def test_geracao_reprodutivel() -> None:
    # mesma semente -> mesmos eventos
    _, ev1, _ = syn.generate(n_events=200, seed=7)
    _, ev2, _ = syn.generate(n_events=200, seed=7)
    assert ev1.equals(ev2)


def test_recompensas_referenciam_eventos_validos() -> None:
    _, ev, rw = syn.generate(n_events=200, seed=1)
    assert set(rw["event_id"]).issubset(set(ev["event_id"]))
    assert set(rw["reward_type"]).issubset({"click", "journey_start", "conversion"})
