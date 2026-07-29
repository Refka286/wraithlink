from app.risk_engine.scoring import RiskRating

# ratings reflect the worked examples in Plan_de_Travail_AegisPen.md section 5.3
CATALOG: dict[str, RiskRating] = {
    "nmap:syn-stealth": RiskRating(impact=1, detectability=2, reversibility=5),
    "ldap:anonymous-enum": RiskRating(impact=1, detectability=1, reversibility=5),
    "sqlmap:aggressive": RiskRating(impact=3, detectability=4, reversibility=4),
    "netexec:kerberoast": RiskRating(impact=3, detectability=2, reversibility=5, sensitive=True),
    "ad:bruteforce-massive": RiskRating(impact=4, detectability=5, reversibility=2),
    "netexec:dcsync": RiskRating(impact=5, detectability=1, reversibility=1),
}


class UnknownActionRatingError(KeyError):
    def __init__(self, key: str):
        super().__init__(f"no risk rating registered for '{key}'")
        self.key = key
