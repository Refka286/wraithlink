from app.risk_engine.scoring import RiskRating

# ratings reflect the worked examples in Plan_de_Travail_Wraithlink.md section 5.3
CATALOG: dict[str, RiskRating] = {
    "nmap:syn-stealth": RiskRating(impact=1, detectability=2, reversibility=5),
    "ldap:anonymous-enum": RiskRating(impact=1, detectability=1, reversibility=5),
    "sqlmap:aggressive": RiskRating(impact=3, detectability=4, reversibility=4),
    "netexec:kerberoast": RiskRating(impact=3, detectability=2, reversibility=5, sensitive=True),
    "ad:bruteforce-massive": RiskRating(impact=4, detectability=5, reversibility=2),
    "netexec:dcsync": RiskRating(impact=5, detectability=1, reversibility=1),
    # not in the original worked table, but rated on the same basis as the
    # entries above: default wordlist/templates stay read-only and quiet,
    # aggressive modes behave like the sqlmap:aggressive entry
    "ffuf:default": RiskRating(impact=1, detectability=3, reversibility=5),
    "nuclei:default": RiskRating(impact=1, detectability=2, reversibility=5),
    "nuclei:aggressive": RiskRating(impact=3, detectability=4, reversibility=4),
    # BloodHound collection is LDAP/SMB enumeration with a valid low-priv
    # account, same nature as the anonymous LDAP enum example above
    "bloodhound:collect": RiskRating(impact=1, detectability=2, reversibility=5),
    # a ZAP full/active scan sends live attack traffic, same nature as the
    # sqlmap:aggressive entry - the plan explicitly keeps this out of the
    # automatic tier regardless of numeric score
    "zap:active-scan": RiskRating(impact=3, detectability=4, reversibility=4, sensitive=True),
}


class UnknownActionRatingError(KeyError):
    def __init__(self, key: str):
        super().__init__(f"no risk rating registered for '{key}'")
        self.key = key
