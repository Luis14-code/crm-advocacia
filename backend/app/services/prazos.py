"""Cálculo de prazos processuais em dias úteis.

Considera (Seção 9.3):
- Fins de semana
- Feriados nacionais fixos e móveis (Páscoa → Carnaval, Sexta Santa, Corpus Christi)
- Recesso forense / suspensão de prazos (CPC art. 220): 20/12 a 20/01

Observação: feriados estaduais/municipais não são universais; o escritório pode
estender FERIADOS_EXTRA conforme a comarca.
"""
from datetime import date, timedelta
from functools import lru_cache

# Feriados estaduais/municipais adicionais (date) definidos pelo escritório.
FERIADOS_EXTRA: set[date] = set()


def _pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Butcher)."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    mes = (h + ll - 7 * m + 114) // 31
    dia = ((h + ll - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


@lru_cache(maxsize=32)
def feriados_nacionais(ano: int) -> frozenset[date]:
    pascoa = _pascoa(ano)
    fixos = [
        date(ano, 1, 1),    # Confraternização Universal
        date(ano, 4, 21),   # Tiradentes
        date(ano, 5, 1),    # Dia do Trabalho
        date(ano, 9, 7),    # Independência
        date(ano, 10, 12),  # Nossa Senhora Aparecida
        date(ano, 11, 2),   # Finados
        date(ano, 11, 15),  # Proclamação da República
        date(ano, 11, 20),  # Consciência Negra (nacional desde 2024)
        date(ano, 12, 25),  # Natal
    ]
    moveis = [
        pascoa - timedelta(days=48),  # Carnaval (segunda)
        pascoa - timedelta(days=47),  # Carnaval (terça)
        pascoa - timedelta(days=2),   # Sexta-feira Santa
        pascoa + timedelta(days=60),  # Corpus Christi
    ]
    return frozenset(fixos + moveis)


def em_recesso(d: date) -> bool:
    """Suspensão de prazos (CPC 220): 20/12 a 20/01."""
    if d.month == 12 and d.day >= 20:
        return True
    if d.month == 1 and d.day <= 20:
        return True
    return False


def eh_dia_util(d: date) -> bool:
    if d.weekday() >= 5:  # 5=sábado, 6=domingo
        return False
    if d in feriados_nacionais(d.year):
        return False
    if d in FERIADOS_EXTRA:
        return False
    if em_recesso(d):
        return False
    return True


def proximo_dia_util(d: date) -> date:
    atual = d
    while not eh_dia_util(atual):
        atual += timedelta(days=1)
    return atual


def adicionar_dias_uteis(inicio: date, dias: int) -> date:
    """Prazo processual: conta `dias` dias úteis a partir do 1º dia útil seguinte."""
    atual = inicio
    restantes = dias
    while restantes > 0:
        atual += timedelta(days=1)
        if eh_dia_util(atual):
            restantes -= 1
    return atual


def contar_dias_uteis(inicio: date, fim: date) -> int:
    """Dias úteis entre duas datas (exclui o início, inclui o fim)."""
    if fim <= inicio:
        return 0
    total = 0
    atual = inicio
    while atual < fim:
        atual += timedelta(days=1)
        if eh_dia_util(atual):
            total += 1
    return total


def data_limite_util(data_limite: date) -> date:
    """Se a data-limite cair em dia não útil, prorroga para o próximo dia útil."""
    return proximo_dia_util(data_limite)
