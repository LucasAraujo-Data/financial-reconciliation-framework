# Business Requirements

## 1. Project Overview

This project simulates a financial organization that records transactions across two independent systems:

* an operational source system;
* an accounting and reporting system.

Both systems are expected to contain equivalent financial information. However, differences may arise because of data processing delays, duplicated transactions, missing records, reprocessing, foreign exchange conversion, rounding, incorrect mappings or data quality issues.

The objective is to build an automated financial reconciliation and data quality framework that compares both systems, identifies discrepancies, classifies exceptions and produces audit-ready reports.

## 2. Business Problem

The finance team currently performs monthly reconciliation using spreadsheets and manual comparisons.

This process creates several risks:

* delayed monthly closing;
* inconsistent reconciliation criteria;
* undetected duplicated or missing transactions;
* limited traceability;
* excessive manual investigation;
* difficulty identifying recurring root causes;
* lack of historical monitoring;
* dependency on individual analysts.

The organization requires a standardized and reproducible reconciliation process.

## 3. Business Objective

The framework must automate the comparison between the operational and accounting systems and provide finance analysts with a prioritized list of exceptions requiring investigation.

The solution should help the organization:

* reduce manual reconciliation effort;
* detect material financial differences;
* improve data quality;
* accelerate the monthly closing process;
* increase auditability;
* identify recurring causes of discrepancies;
* monitor reconciliation performance over time.

## 4. Stakeholders

### Finance Analyst

Reviews reconciliation results, investigates exceptions and determines corrective actions.

### Finance Manager

Monitors monthly closing progress, material differences and unresolved exceptions.

### Data Engineering Team

Maintains source data pipelines and resolves structural data quality issues.

### Accounting Team

Validates accounting records, financial periods and posting rules.

### Internal Audit

Reviews reconciliation controls, rule consistency and historical evidence.

## 5. In-Scope Data

The initial version of the framework will reconcile financial transactions containing:

* transaction identifier;
* contract identifier;
* counterparty identifier;
* transaction type;
* accounting period;
* transaction date;
* currency;
* original amount;
* exchange rate;
* converted amount;
* source system;
* processing timestamp.

The project will use synthetic data generated specifically for this portfolio.

No confidential or proprietary company information will be used.

## 6. Reconciliation Grain

The primary reconciliation grain will be:

> contract_id + counterparty_id + transaction_type + accounting_period + currency

Individual transaction-level analysis will also be available for detailed investigation.

The selected grain represents the business dimensions required to compare financial balances across systems.

## 7. Reconciliation Scenarios

The framework must identify at least the following outcomes:

### Matched

A corresponding record exists in both systems and the financial difference is within the configured tolerance.

### Amount Mismatch

A corresponding record exists in both systems, but the financial difference exceeds the configured tolerance.

### Missing in Source System

A record exists in the accounting system but does not exist in the operational system.

### Missing in Accounting System

A record exists in the operational system but does not exist in the accounting system.

### Duplicate Transaction

The same business transaction appears more than once in one of the systems.

### Currency Conversion Difference

The original amounts match, but converted amounts differ because of exchange rate differences.

### Accounting Period Mismatch

The same transaction exists in both systems but was recorded in different accounting periods.

### Reprocessed Transaction

A transaction was replaced or processed again, creating different versions or timestamps.

### Mapping Error

The financial amount matches, but one or more business dimensions were assigned incorrectly.

### Invalid Record

A record violates required schema or business rules.

## 8. Materiality Rules

The framework must support configurable reconciliation tolerances.

Initial rules:

* absolute tolerance: USD 0.01;
* relative tolerance: 0.10%;
* high-value exception threshold: USD 10,000;
* critical exception threshold: USD 100,000.

The rules must be stored outside the Python source code so that they can be changed without modifying the reconciliation logic.

## 9. Functional Requirements

The system must:

1. generate reproducible synthetic financial datasets;
2. ingest records from two simulated systems;
3. validate schemas and mandatory fields;
4. detect duplicated records;
5. standardize dates, currencies and numerical fields;
6. aggregate records using the defined reconciliation grain;
7. match corresponding records across systems;
8. calculate absolute and relative differences;
9. apply configurable tolerances;
10. classify reconciliation outcomes;
11. assign severity levels;
12. generate detailed exception records;
13. generate reconciliation summary metrics;
14. export an Excel exception report;
15. save pipeline execution logs;
16. retain historical reconciliation results;
17. provide analytical tables for a Power BI dashboard.

## 10. Non-Functional Requirements

The solution should be:

### Reproducible

Synthetic data generation and pipeline execution must produce consistent results when the same random seed is used.

### Configurable

Tolerance thresholds and reconciliation rules must be stored in configuration files.

### Testable

Core reconciliation rules must have automated unit tests.

### Traceable

Each pipeline execution must produce a run identifier and execution timestamp.

### Auditable

The framework must preserve sufficient information to explain why each record received its reconciliation status.

### Modular

Data generation, ingestion, validation, reconciliation and reporting must be implemented as separate components.

### Maintainable

Code must use clear naming, type hints, documentation and structured logging.

### Secure

No passwords, credentials or sensitive data may be committed to the repository.

## 11. Key Performance Indicators

The framework will calculate:

* total source amount;
* total accounting amount;
* net financial difference;
* absolute financial difference;
* reconciliation match rate;
* exception rate;
* number of exceptions;
* exception amount;
* material exception amount;
* exceptions by type;
* exceptions by severity;
* exceptions by accounting period;
* exceptions by counterparty;
* unresolved exception aging;
* duplicate transaction rate;
* invalid record rate.

## 12. Success Criteria

The first release will be considered successful when:

* the complete pipeline runs from a single command;
* all intentionally injected anomaly types are detected;
* reconciliation results are reproducible;
* material exceptions are correctly prioritized;
* unit tests cover the main reconciliation rules;
* an Excel exception report is generated;
* analytical outputs can be consumed by Power BI;
* project documentation allows another analyst to understand and execute the solution.

## 13. Out of Scope

The first release will not include:

* real bank or insurance data;
* direct integration with enterprise financial systems;
* automated journal entry creation;
* user authentication;
* real-time streaming;
* cloud production deployment;
* automatic correction of financial records;
* machine learning for root-cause prediction.

These capabilities may be considered as future improvements.

## 14. Business Deliverables

The project will deliver:

* synthetic source and accounting datasets;
* configurable reconciliation engine;
* data quality validation process;
* detailed reconciliation results;
* exception prioritization;
* Excel exception report;
* SQL analytical tables;
* Power BI dashboard;
* architecture documentation;
* data dictionary;
* metric dictionary;
* automated tests;
* executive project summary.
