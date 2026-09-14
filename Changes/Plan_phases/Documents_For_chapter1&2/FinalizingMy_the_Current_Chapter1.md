
# SafeBooks: A Secure Financial Records Monitoring System with Tax Compliance Tracking and Predictive Risk Analytics


# CHAPTER 1

# INTRODUCTION

## Background of the Study

Managing financial records and fulfilling tax compliance obligations for multiple client businesses simultaneously has become an increasingly complex responsibility for bookkeeping professionals worldwide. As the number of client businesses they manage grows, so does the volume of financial transactions, tax figures, and tax authority requirements that must be accurately recorded, monitored, and processed on behalf of each client. Studies have demonstrated that the absence of structured financial record management systems directly affects the accuracy, consistency, and growth potential of business financial operations [1]. Without digital tools that consolidate client records, financial tracking, and compliance monitoring into a single organized platform, bookkeeping professionals are forced to rely on manual methods that are prone to errors, inconsistencies, and missed financial obligations.

The Philippine government has been actively advancing digital transformation in tax administration through the Bureau of Internal Revenue, which has expanded its digital platforms including the Electronic Filing and Payment System, eBIRForms, and the Online Registration and Update System to modernize tax filing and payment processes for businesses nationwide [2]. While these platforms have significantly improved tax administration at the government level, bookkeepers who assist client businesses in navigating BIR requirements continue to manage their own client records and compliance monitoring through manual and disconnected methods. This creates a persistent gap between the availability of government digital tax platforms and the actual tools that bookkeeping professionals use to manage their clients' financial data daily.

This study directly supports United Nations Sustainable Development Goal 9: Industry, Innovation and Infrastructure, which promotes the development of technology-driven solutions that advance digital innovation and strengthen productive capacity across industries [3]. It is likewise anchored on the Davao del Norte State College Research, Development, and Extension Agenda under its Strategic Development Plan 2025 to 2029, which emphasizes technology-driven community solutions that contribute to regional socio-economic development [4].

Home-based bookkeepers in Panabo City, Davao del Norte serve as both financial recorders and tax compliance assistants, managing monthly financial transactions, computing tax obligations, and processing BIR requirements for multiple client businesses simultaneously. These bookkeepers currently rely on a paper-based folder system where each folder contains all financial records and BIR-related information for a specific client business. When tax due dates approach, locating the correct client record becomes time-consuming and inefficient, particularly when clients share similar names or when one client owns multiple businesses. Since no mechanism exists for fast record retrieval, bookkeepers must check records manually to locate the correct business, causing delays that affect the timely processing of client tax obligations. The absence of a Taxpayer Identification Number-based search function is a significant gap, as the TIN is a unique identifier that could allow bookkeepers to locate the exact business record they need quickly and accurately.

Beyond record retrieval, the current approach creates deeper analytical gaps. Monthly financial and compliance data are recorded inconsistently across paper documents with no organized history. Without a financial analytics engine, bookkeepers cannot identify meaningful trends in their clients' financial data. The lack of a risk classification mechanism means there is no systematic way to determine which client businesses are financially stable or at risk. Most critically, the absence of any forecasting capability means potential financial concerns can only be recognized after problems have already emerged, limiting the bookkeeper's ability to provide timely and proactive advisory support. Additionally, sensitive client information including TIN numbers, BIR credentials, and financial records stored in physical documents remain entirely unprotected due to the absence of any security mechanism.

To address these challenges, this study proposes **SafeBooks: A Secure Financial Records Monitoring System with Tax Compliance Tracking and Rule-based Forecasting and Risk Analytics**. The system centralizes client profiles and monthly financial record management, and provides a Taxpayer Identification Number (TIN) search to speed and improve record retrieval. It includes a Financial Analytics Engine that produces descriptive summaries and a rule-based, trend-oriented forecasting method (not a machine-learning model) to surface recent movement in client finances. Risk classification is implemented as a rule-based field on the client record (`risk level`) that flags Low, Medium, or High risk and supports short advisory notes. The platform uses secure authentication and account controls to protect sensitive client information. SafeBooks does not perform direct integration with external BIR APIs; any claims of automatic BIR integration have been clarified or removed. The system will be evaluated through assessments of usability, functional accuracy, and its effectiveness in supporting financial monitoring and advisory decision-making among the target users.

---

# Objectives of the Study


The primary objective of this study is to develop **SafeBooks: A Secure Financial Records Monitoring System with Tax Compliance Tracking and Predictive Risk Analytics** that centralizes client financial record management, supports tax compliance monitoring, and strengthens advisory decision-making through descriptive analytics, trend-based forecasting, and risk classification.

Specifically, the study aims to:

1. Design and implement a centralized and secure client profile management component that stores essential business and taxpayer information, supports search using the Taxpayer Identification Number, and protects access to authorized bookkeeper accounts.

2. Develop a monthly financial records tracking component that organizes period-based entries, accommodates multiple line items, applies validation rules, and generates structured totals and summaries.

3. Build a Financial Analytics Engine that summarizes sales, expenses, and tax-related entries, presents monthly trend patterns, and produces simple forecasting insights based on recorded financial movement.

4. Establish a rule-based risk classification feature that categorizes clients as Low, Medium, or High Risk and provides advisory guidance to support timely monitoring and follow-up.

5. Create an integrated dashboard and reporting interface that presents risk classifications, financial trend summaries, forecasting insights, compliance statuses, and organized report outputs for bookkeeper use.

---

# Significance of the Study

This study develops **SafeBooks: A Secure Financial Records Monitoring System with Tax Compliance Tracking and Predictive Risk Analytics** to support bookkeeping professionals in managing client financial records, monitoring tax compliance obligations, and making informed advisory decisions through analytics and risk classification. The findings and outcomes of this study are expected to provide direct and meaningful value to the following stakeholders:

### Bookkeepers

As the primary users of the system, bookkeepers will benefit most from its development. SafeBooks provides a centralized workspace for managing client profiles, monthly financial records, analytics, and reporting in one accessible platform. Its TIN-based search feature supports faster record retrieval, while the analytics and trend-based forecasting tools help bookkeepers review financial movement and identify entries that may require closer attention. The dashboard, reporting interface, and risk classification displays further support timely monitoring and more organized advisory work.

### Client Businesses

Businesses whose financial records are managed by bookkeepers will benefit from more accurate, consistent, and organized financial record management. By centralizing client information, monthly entries, and related compliance details, the system helps reduce the risks associated with misplaced records, delayed follow-up, and inconsistent tracking. The analytics and risk classification features also provide earlier visibility into financial concerns, allowing bookkeepers to support client businesses with more timely guidance.

### Local Bookkeeping Organization

The bookkeeping organization to which the target users are affiliated will benefit indirectly as its member bookkeepers improve the efficiency and consistency of their financial monitoring and advisory services through the system. The structured summaries, dashboard views, and report outputs generated by SafeBooks may also serve as useful references for training, shared procedures, and the promotion of better financial record management practices among its members and the local business community they serve.

---

## Scope and Limitation

This section presents the study's scope and its constraints in the order requested by the supervising faculty: People, Technology, Data, and Process.

The primary users are home-based bookkeepers affiliated with a local bookkeeping organization in Panabo City, Davao del Norte. Administrators are included in the platform as operational support users responsible for tasks such as account approval, basic user management, and workspace configuration; administrator responsibilities are limited to maintaining system continuity and are not the primary focus of this study.

SafeBooks is implemented as a web-based application accessible from standard laptops and desktop computers. It employs common web technologies and secure authentication to control access. The platform is intended for ordinary computing environments and does not require specialized hardware.

The system stores client business profiles (including taxpayer identifiers such as the Taxpayer Identification Number), monthly financial records, and tax-related entries entered manually by bookkeepers. Input validation is applied during data entry to promote completeness and consistency. The dataset produced through normal use supports reporting, dashboard views, and rule-based analytics.

Key processes supported by the platform include centralized client profile management, period-based financial record entry with multiple line items, a Financial Analytics Engine that produces descriptive summaries and rule-based trend forecasts, a rule-based risk classification feature, and dashboard/reporting interfaces to support bookkeeping workflows.

The evaluation and intended deployment are limited to the identified home-based bookkeepers and their affiliated organization; the system is not designed for government agencies, commercial accounting firms, or organizations outside the specified user group.

As a prototype, SafeBooks does not incorporate machine learning nor does it perform automated integration with external BIR platforms (for example, the Electronic Filing and Payment System or eBIRForms). The study does not evaluate operation on specialized server hardware.

All outputs depend on manually entered records; therefore, accuracy and reliability are contingent on the completeness and correctness of user input. The system records tax figures as entered by bookkeepers and does not automatically compute tax liabilities. Formal security certification or third-party audits are outside the scope of this study.

Analytical outputs (trend forecasts and risk classifications) are produced using predefined rules applied to recorded data rather than probabilistic or machine-learned models. SafeBooks does not implement full accounting functionality; its outputs are constrained by the available input data and the rule definitions present in the system.

---
---

# Review of Related Literature and Works

## Related Literature

The increasing complexity of financial record management and tax compliance has accelerated adoption of digital tools that structure bookkeeping workflows and improve access to financial information. This subsection reviews literature on recordkeeping, tax technology, financial analytics, forecasting, and classification to establish the foundations for SafeBooks.

Structured recordkeeping and access to finance are recognized as catalysts for small-enterprise resilience and planning. Development reports indicate that improved record practices and basic digital financial tools increase the reliability of information used for business decisions and reporting [5].

Digital tax platforms and e‑government services can raise compliance and reduce administrative burden, but they are typically designed for direct taxpayer interaction rather than intermediary users such as bookkeepers. Okunogbe and Pouliquen show that electronic tax filing initiatives improve compliance at scale [6].

Research on accounting information systems highlights how internet-enabled tools improve financial visibility and enable more timely monitoring of financial activity. Moll and Yigitbasioglu document changes in accounting work practices when digital systems provide consolidated transaction views and automated summaries [7].

The integration of analytics into accounting environments has been shown to enhance managerial decision-making. Appelbaum et al. discuss how descriptive and predictive analytics embedded in enterprise systems support timely actions [8], and Warren et al. show that data-driven approaches help practitioners identify trends and anticipate outcomes [9].

Forecasting methods that prioritize interpretability are appropriate for small-scale bookkeeping applications; Hyndman and Athanasopoulos provide guidance on parsimonious approaches that favor clarity and usability [10].

Classification techniques using financial indicators are widely used in risk assessment for firms. Delen et al. demonstrate that decision-tree and ratio-based classifiers can categorize financial health and support early warning systems [11].

---

# Definition of Terms

Advisory decision-making: The process by which a bookkeeper interprets financial information and system-generated summaries to provide practical, context-aware recommendations to a client business.

Bookkeeper: The primary user role responsible for entering client transactions, maintaining period-based records, and using the system's dashboards and reports to monitor client finances.

Administrator: A supporting user role responsible for operational tasks such as account approvals, basic user management, and workspace configuration; administrator functions are limited and not the primary focus of this study.

Client profile: A consolidated record that stores a client's identifying details (including Taxpayer Identification Number), business information, contact data, and configuration used by the system to group financial records.

Financial record: A period-based record of transactions for a client, consisting of multiple line items (sales, expenses, taxes) and summarized totals for that period.

Financial analytics engine: The system component that computes descriptive summaries, type breakdowns (e.g., sales, expenses, tax), simple normalized trends, and rule-based forecasting signals from recorded financial data.

Descriptive analytics: Techniques that summarize historical financial data to reveal patterns, monthly movement, and component breakdowns useful for bookkeeping review and reporting.

Forecasting: A rule-based, trend-oriented projection of near-term financial direction derived from recent recorded patterns; designed for interpretability rather than probabilistic prediction.

Risk classification: An interpretable, rule-based categorization of a client's financial condition (Low, Medium, High) based on heuristic checks and recent financial movement to support prioritized follow-up.

Dashboard: A consolidated, user-facing interface that presents client lists, risk indicators, monthly summaries, and links to detailed records and reports.

Integrated reporting: Structured exportable reports that combine financial summaries, compliance status, and risk notes for bookkeeping workflows and client communication.

Tax compliance monitoring: Tracking of tax-related fields and deadlines recorded by the bookkeeper to support timely filing and advisory actions; does not replace governmental filing systems.

Taxpayer Identification Number (TIN): The official identifier used by government tax authorities; in SafeBooks it is a key field for precise client search and record retrieval.

TIN-based search: A search function that locates client profiles and associated records by matching the Taxpayer Identification Number.

Secure authentication: Application-level mechanisms (password-based accounts, optional two-factor setup, access controls) that restrict data access to authorized users.

Web-based system: A platform accessible via web browsers on standard computing devices; SafeBooks is delivered as a browser-accessible prototype and does not require specialized hardware.


# References

[1] C. Mintah, M. Gabir, F. Aloo, and E. K. Ofori, "Do business records management affect business growth?" *PLOS ONE*, vol. 17, no. 3, p. e0264135, Mar. 2022. [Online]. Available: https://pmc.ncbi.nlm.nih.gov/articles/PMC8912245/. [Accessed: Mar. 2026].

[2] Bureau of Internal Revenue, "Strategic Plan 2024-2028," *BIR Official Website*, 2024. [Online]. Available: https://bir-cdn.bir.gov.ph/BIR/pdf/Strategic%20Plan%20Annex%20A.pdf. [Accessed: Mar. 05, 2026].

[3] United Nations Department of Economic and Social Affairs, "Transforming our world: The 2030 Agenda for Sustainable Development," [Online]. Available: https://sdgs.un.org/2030agenda. [Accessed: Mar. 05, 2026].

[4] Davao del Norte State College, "DNSC PRMO facilitates 2nd workshop on the development of the DNSC Strategic Plan 2025-2029," *DNSC Official Website*, May 2024. [Online]. Available: https://dnsc.edu.ph/dnsc-prmo-facilitates-2nd-workshop-on-the-development-of-the-dnsc-strategic-plan-2025-2029. [Accessed: Mar. 05, 2026].

[5] World Bank, "SME Finance and Development," World Bank. [Online]. Available: https://www.worldbank.org/en/topic/smefinance. [Accessed: May 24, 2026].

[6] O. Okunogbe and V. Pouliquen, "Technology, Taxation, and Corruption: Evidence from the Introduction of Electronic Tax Filing," *American Economic Journal: Economic Policy*, vol. 14, no. 1, pp. 341-372, Feb. 2022. [Online]. Available: https://www.aeaweb.org/articles?id=10.1257/pol.20200123. [Accessed: Apr. 2026].

[7] J. Moll and O. Yigitbasioglu, "The role of internet-related technologies in shaping the work of accountants: New directions for accounting research," *The British Accounting Review*, vol. 51, no. 6, p. 100833, 2019. [Online]. Available: https://www.sciencedirect.com/science/article/abs/pii/S0890838919300459. [Accessed: Apr. 2026].

[8] D. Appelbaum, A. Kogan, M. Vasarhelyi, and Z. Yan, "Impact of business analytics and enterprise systems on managerial accounting," *International Journal of Accounting Information Systems*, vol. 25, pp. 29-44, May 2017. [Online]. Available: https://www.sciencedirect.com/science/article/abs/pii/S1467089517300490. [Accessed: Apr. 2026].

[9] J. D. Warren, K. C. Moffitt, and P. Byrnes, "How Big Data Will Change Accounting," *Accounting Horizons*, vol. 29, no. 2, pp. 397-407, Jun. 2015. [Online]. Available: https://publications.aaahq.org/accounting-horizons/article-abstract/29/2/397/2168. [Accessed: Apr. 2026].

[10] R. J. Hyndman and G. Athanasopoulos, "Forecasting: Principles and Practice," 3rd ed., OTexts, 2021. [Online]. Available: https://otexts.com/fpp3/. [Accessed: May 24, 2026].

[11] D. Delen, C. Kuzey, and A. Uyar, "Measuring firm performance using financial ratios: A decision tree approach," *Expert Systems with Applications*, vol. 40, no. 10, pp. 3970-3983, Aug. 2013. [Online]. Available: https://www.sciencedirect.com/science/article/abs/pii/S0957417413000158. [Accessed: Apr. 2026].