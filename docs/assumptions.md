# Project Assumptions

1. All project data is synthetic.
2. USD is the reporting currency.
3. Transactions may originate in USD, BRL, EUR or GBP.
4. Both systems should represent the same underlying financial activity.
5. Data may arrive at different processing times.
6. Small rounding differences may be accepted according to configured tolerances.
7. Reconciliation is executed monthly.
8. Financial records are immutable after ingestion, except when explicitly marked as reprocessed.
9. Every pipeline execution receives a unique run identifier.
10. Exceptions are identified automatically but resolved manually.
11. The first release processes batch files rather than real-time events.
12. Synthetic anomalies are intentionally injected to test the framework.