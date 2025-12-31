from .base import BordaCountStrategy, ChairmanCutStrategy

STRATEGIES = {
    "borda": BordaCountStrategy(),
    "chairman": ChairmanCutStrategy()
}

def get_strategy(name: str):
    return STRATEGIES.get(name, STRATEGIES["borda"])
