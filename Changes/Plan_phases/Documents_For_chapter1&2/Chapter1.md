# CHAPTER 1

# INTRODUCTION

## Background of the Study

Managing financial records and monitoring compliance-related information for multiple client businesses is a complex responsibility for bookkeeping professionals worldwide. Bookkeepers must maintain accurate records while ensuring that the information for each client remains organized and available when needed. As the number of clients increases, the volume of financial transactions, schedules, notes, and business information that must be recorded and reviewed also grows. Proper business records management supports access to reliable information for planning and decision-making [1]. In addition, research on web-based accounting indicates that online record processing can improve the efficiency of financial tasks such as bank reconciliation, showing the practical value of accessible digital tools in financial management [2].

In the Philippines, the Bureau of Internal Revenue (BIR) continues to expand its digital services to make tax administration and taxpayer transactions more accessible. One of these services is the Online Registration and Update System (ORUS), which supports taxpayer registration and the updating of registration information [3]. The BIR Strategic Plan 2024–2028 further sets the agency’s direction toward a highly digital tax administration system and improved taxpayer services [4]. Although these government platforms support official tax-related transactions, they are not designed as internal workspaces where bookkeepers can manage the records and schedules of several client businesses. Bookkeepers must therefore organize, review, and prepare each client’s information before proceeding to the appropriate BIR service.

Locally, accounting information systems have been examined among agri-related cooperatives in Davao del Norte, particularly in relation to the usefulness of accounting information when responding to operational uncertainty [5]. Another Philippine study found that micro and small businesses experienced difficulties in maintaining accurate accounting records because of inadequate recording practices and limited accounting knowledge [6]. These concerns are relevant to bookkeeping environments where several client businesses are handled because the work involves maintaining client profiles, recording financial transactions, monitoring schedules, and keeping related notes. When this information is distributed across separate files, spreadsheets, or manually maintained records, locating and reviewing the details of a particular client can require additional time and effort. A centralized client-management system that allows records to be searched by client name or TIN can help bookkeepers locate the intended business record more directly and keep its related information in one place.

The project is aligned with selected national and institutional directions that support applied digital solutions. The CHED A.C.H.I.E.V.E. Agenda promotes SDG-based research and innovation that responds to real-world challenges; SafeBooks reflects this direction by applying a web-based record and analytics platform to an identified bookkeeping concern [7]. The DOST Harmonized National Research and Development Agenda 2022–2028 recognizes ICT as an enabler of innovation and includes cloud computing and cyber resilience among its ICT priorities, which relate to the proposed managed web deployment and security controls of SafeBooks [8]. At the institutional level, the DNSC RDE Agenda 2026–2030 places ICT for Development under Innovation and Inclusion and promotes digital tools for grassroots development; SafeBooks supports this direction by addressing the record-management needs of local home-based bookkeepers through an applied information system [9].

Despite the growing adoption of digital financial systems, many existing platforms are intended for general accounting operations, tax-related transactions, or the management of a single business. These platforms provide useful accounting and reporting functions, but their workflows may not directly address the daily record-management needs of home-based bookkeepers handling several client businesses. In this setting, client information, period-based financial records, schedules, remarks, and financial summaries must be managed across different clients. The reviewed studies and systems do not present these functions together with forecasting analytics and internal compliance-related monitoring in one workflow intended for this group of users. This practical gap supports the development of a centralized bookkeeping platform for managing multiple client records.

To address these concerns, this study proposes SafeBooks: A Web-Based Financial Records and Compliance Monitoring System with Forecasting Analytics. The system provides an authenticated web platform with separate access for Bookkeepers and the system administrator, while centralizing client profiles and allowing records to be searched by client name or TIN. Bookkeepers can create period-based financial records containing transaction details, monthly, quarterly, or annual frequencies, deadlines, and notes, while client remarks and internal indicators assist in monitoring recorded entries and schedules. Its financial analytics component summarizes sales, expenses, tax-related amounts, and net values across periods, and historical transaction records are used to generate forecasts through the selected Seasonal Autoregressive Integrated Moving Average (SARIMA) model. SafeBooks is limited to internal record management and monitoring; it does not calculate official tax liabilities, submit tax returns, confirm official BIR compliance, or replace the BIR’s electronic services.


**Objectives of the Study**
The primary objective of this study is to develop SafeBooks, a web-based platform that supports home-based bookkeepers in organizing multiple client records, monitoring compliance-related schedules, and reviewing financial information through descriptive and forecasting analytics.
Specifically, the study aims to:
1. Digitize client business profiles, historical financial records, transaction details, record schedules, deadlines, remarks, and supporting notes.
2. Design and develop a centralized web-based workspace for maintaining client profiles and related bookkeeping records, with search using the client name or TIN.
3. Implement period-based financial records for manually encoded sales, expenses, tax-related entries, deadlines, and notes, with each record assigned a monthly, quarterly, or annual frequency.
4. Compare Weighted Moving Average (WMA), Holt-Winters Exponential Smoothing, and Seasonal Autoregressive Integrated Moving Average (SARIMA) using a time-based holdout of historical client financial records and the Mean Absolute Error (MAE), Mean Absolute Percentage Error (MAPE), Root Mean Square Error (RMSE), and Weighted Absolute Percentage Error (WAPE) metrics to determine a suitable forecasting model.
5. Generate descriptive summaries, financial trends, and forecasts from recorded financial data using the selected SARIMA model.
6. Generate dashboard and analytics outputs that provide financial summaries, upcoming deadlines, client remarks, and forecasting results, together with printable client financial reports for bookkeeping review and follow-up.

**Significance of the Study**
The development of SafeBooks: A Web-Based Financial Records and Compliance Monitoring System with Forecasting Analytics is intended to support the organization of bookkeeping records, the monitoring of compliance-related schedules, and the review of financial information among its intended users.

**Home-Based Bookkeepers.** The primary beneficiaries of the proposed system are home-based bookkeepers who manage multiple client businesses. SafeBooks provides a centralized workspace for maintaining client profiles, financial records, schedules, remarks, and supporting notes. Its search function allows a bookkeeper to locate a client record using the client name or TIN. Descriptive financial summaries and SARIMA forecasts provide additional information for reviewing recorded financial activity and recognizing changes that may require closer examination. These functions can lessen the need to move between separate records and support a more consistent bookkeeping workflow.

**System Administrators.** System administrators may benefit from tools for reviewing registration requests, approving or rejecting Bookkeeper accounts, managing account status, and reviewing recorded user activities. Separate administrative access supports the oversight of Bookkeeper accounts and provides an activity record that can be reviewed when necessary.

**Client Businesses.** Client businesses may benefit indirectly when their bookkeepers use a more organized process for maintaining and reviewing financial records. Financial summaries, forecasting results, and printable client reports can provide a clearer basis for discussing recorded financial activity with the bookkeeper. These outputs may support more consistent record review and follow-up without replacing professional accounting procedures or official BIR services.

**Bookkeepers Guild of Panabo City Inc.** The study may benefit the organization by demonstrating how a centralized web-based platform can support bookkeeping activities involving multiple client businesses. SafeBooks may provide its members with a practical reference for organizing client records, reviewing financial summaries, and monitoring record schedules through a single workspace. The study may also serve as a basis for considering similar digital approaches in future bookkeeping activities or initiatives.

**Scope and Limitation**
The primary users of SafeBooks are home-based bookkeepers affiliated with a local bookkeeping organization in Panabo City, Davao del Norte. Each Bookkeeper manages the profiles and financial records of multiple client businesses through an individual account. The platform also includes a System Administrator who reviews account registrations, approves or rejects applications, manages Bookkeeper account status, and reviews recorded system activities. Client businesses do not directly operate the platform but may receive financial reports prepared by their bookkeepers.

SafeBooks is a web-based platform developed using Python and the Django framework, with PostgreSQL used for database management. Its user interface is built with Django Templates, HTML, CSS, and JavaScript for access through desktop and laptop web browsers. Configured email services support account verification, approval notifications, and login alerts. PyOTP supports two-factor authentication for the System Administrator.

The system stores Bookkeeper account information, client business profiles, TINs, business details, financial records, and related audit entries. Financial records may contain transaction details for sales, expenses, and tax-related amounts, together with monthly, quarterly, or annual frequencies, deadlines, and notes. Client profiles may also contain remarks and other details needed by the Bookkeeper. These records provide the data used for financial summaries, trend views, SARIMA forecasts, and printable client reports.

The supported workflow begins with Bookkeeper registration, email verification, and System Administrator approval. Once approved, a Bookkeeper can maintain client profiles, search for a client by name or TIN, and create period-based financial records. SafeBooks processes recorded information into dashboard summaries, financial analytics, internal schedule monitoring, and SARIMA forecasts when sufficient, regularly spaced historical data are available. The Bookkeeper can then review these outputs and prepare a printable financial report for a selected client.

The implementation, evaluation, and intended use of SafeBooks are limited to the identified home-based bookkeepers and their affiliated organization in Panabo City, Davao del Norte. It is not designed for government agencies, commercial accounting firms, enterprise accounting operations, or organizations outside the identified user group. Client businesses are indirect beneficiaries and are not provided with their own system accounts. Findings from the study are therefore limited to the users and setting covered by the project.

The platform is limited to the technologies and web-based environment implemented in the study. Its operation requires a compatible web browser, an appropriate device, and access to the configured network or hosting environment. SafeBooks does not use artificial intelligence, machine learning, or blockchain technology for its forecasting and record-management functions. It also does not connect directly to external BIR platforms such as ORUS, eFPS, or eBIRForms.

The system relies on financial and tax-related information manually encoded by the Bookkeeper. It does not independently verify entries against source documents, official taxpayer records, or information held by the BIR. SARIMA forecasting requires sufficient, regularly spaced historical observations corresponding to the applicable reporting frequency. Incomplete, inaccurate, irregular, or insufficient records may therefore prevent forecasting or affect the financial summaries, trends, and forecast results produced by the system.

SafeBooks is limited to internal financial record management, analytics, and compliance-related schedule monitoring. It does not calculate official tax liabilities, submit tax returns, determine or confirm official BIR compliance, or replace established bookkeeping and accounting procedures. The study evaluates the platform only within the functional, usability, and operational conditions defined for the target users. Formal cybersecurity certification, third-party security auditing, large-scale infrastructure testing, and enterprise-level scalability evaluation are outside the scope of the study.

**Review of Related Literature and Works**
**Related Literature**

**Digital Financial Management and Manual Recordkeeping**

Web-based financial platforms bring record storage, monitoring, and visual summaries into a shared digital environment. A recent review examined systems that combine financial records, dashboards, and analytical functions instead of limiting users to separate tracking tools. The same review also noted that integrated platforms must still address concerns involving privacy, scalability, and the quality of the information being processed [10]. These observations provide a broad basis for considering a centralized platform while avoiding the assumption that digitalization alone resolves every financial-management concern.

Manual bookkeeping remains workable in some settings, but its limitations become more visible as the volume of records increases. An evaluation conducted at PT Javindo Utama reported susceptibility to recording errors and delays in preparing financial statements under its manual process. The findings were specific to that organization, yet they illustrate how repeated manual handling can affect the organization and timely preparation of financial information [11]. For SafeBooks, this concern supports structured digital recordkeeping without claiming that the system removes the Bookkeeper’s responsibility to enter and review accurate information.

**Web-Based Accounting and Client-Server Organization**

Online accounting systems have been examined as a way of supporting particular financial procedures through a web interface. One study focused on bank reconciliation and described how an online accounting environment could organize the information needed for that process. Although SafeBooks does not perform bank reconciliation, the study is relevant because it demonstrates how a defined accounting activity can be transferred from a manual arrangement to a browser-accessible workflow [12]. The connection to the present study is therefore the use of web technology for organized financial-record processing, not the duplication of the study’s reconciliation function.

A web-based platform also depends on the exchange of requests and responses between the user interface and the server. Research on the client-server model explains the roles of network communication and server processing in delivering web-accessible functions [13]. This arrangement allows the interface, application logic, and stored information to work together without requiring the user to manage each technical component directly. SafeBooks follows this general arrangement through a browser interface connected to a Django application and its database.

**Financial Analytics and Forecasting**

Financial analytics adds value to stored records by organizing them into summaries, trends, and other information that can be examined by the user. A study involving management accountants and operational managers found that business intelligence and analytics systems influenced how information was produced, transmitted, and used during decision-related work. Its findings also showed that the effect of analytics depended on how the users worked with the information rather than on the technology alone [14]. SafeBooks reflects this limited role by providing descriptive financial views for Bookkeeper review instead of generating official accounting conclusions or automatic business decisions.

Forecasting extends this process by estimating possible future values from patterns found in historical observations. A large forecasting study compared statistical and machine-learning approaches and cautioned against assuming that greater model complexity always produces better results. This supports evaluating forecasting methods through error measures and selecting a method suited to the available data and purpose of the application [15]. In SafeBooks, SARIMA was selected from the evaluated models as a review aid, and its forecasts remain dependent on the completeness, regularity, and seasonal structure of the client’s recorded financial data.

**Web Application Environment and Philippine Digital Tax Services**

The organization of a web application affects how its interface, processing rules, and stored data operate as a single system. Research on multi-tier web applications discusses the separation of presentation, application, and data responsibilities within a web-based architecture. Such separation provides a useful technical basis for organizing modules while keeping the system accessible through a browser [16]. SafeBooks applies this structure through its web interface, Django-based processing, and PostgreSQL database.

In the Philippines, the BIR uses electronic platforms to support formal taxpayer transactions. Official guidance identifies eFPS and eBIRForms as electronic facilities for filing returns, with eFPS also supporting electronic payment for covered taxpayers [17]. These services are intended for official submission and payment processes rather than the internal organization of records belonging to several client businesses. SafeBooks remains separate from these platforms and prepares no official filing, payment, or confirmation of BIR compliance.

**Synthesis and Research Gap**

The literature covers several concerns that shape the development of SafeBooks: the movement from manual to digital recordkeeping, the use of browser-based accounting processes, the organization of web applications, and the review of stored information through analytics and forecasting. Each source addresses a particular setting, such as general financial platforms, one company’s manual bookkeeping process, bank reconciliation, enterprise analytics, or government tax services. These works provide useful principles, but their users, purposes, and operational boundaries differ from those of the present study. Within the literature reviewed, the same set of ideas is not arranged around the daily workflow of home-based bookkeepers who maintain records for multiple client businesses.

The reviewed literature leaves a practical gap concerning how home-based bookkeepers can manage financial information for multiple client businesses through one internal workflow. Existing studies discuss individual concerns involving digital records, web-based processing, analytics, forecasting, and electronic tax services, but they do not examine their combined use in this specific bookkeeping context. SafeBooks addresses this gap by connecting client record management, period-based financial monitoring, internal schedule tracking, and report preparation within one platform. Its outputs remain separate from official tax computation, filing, payment, and confirmation of compliance. Accordingly, the contribution of the study lies in adapting and integrating established approaches for the needs and responsibilities of its intended users.

**Related Works**

QuickBooks Online, Xero, and Taxumo were reviewed because their accounting, client-management, or tax-related functions are relevant to parts of SafeBooks. The discussion identifies their connection to the study while recognizing that the platforms were developed for different purposes and users.

**QuickBooks Online**

QuickBooks Online Accountant allows accounting practices to access multiple client files, maintain accounting records, and prepare financial reports [18]. It relates to SafeBooks through the organization and review of financial information belonging to several clients. Unlike this broader commercial platform, SafeBooks is limited to the internal workflow defined for the home-based bookkeepers in the study.

**Xero**

Xero provides accounting practices with a centralized view of client information and financial indicators, including balances, receivables, payables, and financial ratios [19]. It relates to SafeBooks through the use of a shared web-based environment for reviewing information from multiple clients. Xero serves wider commercial accounting requirements, whereas SafeBooks applies selected record-monitoring and analytical functions to a more specific bookkeeping workflow.

**Taxumo**

Taxumo is a Philippine online platform that supports tax computation, return filing, payment, income and expense tracking, and the generation of books of accounts [20]. Both platforms handle financial information connected with tax-related work, but SafeBooks is limited to internal record organization and schedule monitoring. It does not calculate official tax liabilities, file returns, process tax payments, or confirm compliance.

**Table 1.** Comparison table of existing system vs. the proposed system.
(See in the Chat i shared an image of it)

Table 1 summarizes the selected functions across the reviewed platforms and SafeBooks. QuickBooks Online and Xero address broader accounting requirements, while Taxumo focuses on Philippine tax transactions. SafeBooks brings selected record-management, monitoring, analytical, and reporting functions into the internal workflow defined for its intended users.

**Definition of Terms**

**Bookkeeper.** The primary user who manages client profiles, maintains period-based financial records, and reviews the resulting summaries, forecasts, and reports.

**Client profile.** A record containing a client’s identifying, business, and contact information. It connects the client with the corresponding financial records and remarks maintained by the Bookkeeper.

**Client remarks.** The classifications used to organize clients as New, Active, Separated, or Closed according to their current bookkeeping relationship.

**Compliance-related schedule monitoring.** The internal tracking of record frequencies and available deadlines to identify client records that may require attention. It does not confirm official filing or compliance with BIR requirements.

**Descriptive analytics.** The system component that generates financial summaries, sales, expense, and tax breakdowns, and trend visualizations from recorded historical data. It describes available records and remains separate from the forecasting component.

**Financial record.** A client-specific entry maintained for a particular period. It contains an entry date, record frequency, notes, transaction details, summarized totals, and a deadline when applicable.

**Forecasting.** The estimation of possible future financial values from the historical transaction data recorded for a client. Forecast results are intended to support review and are not guaranteed financial outcomes.

**Forecasting model evaluation.** The time-based holdout procedure used to assess candidate forecasting models through Mean Absolute Error (MAE), Mean Absolute Percentage Error (MAPE), Root Mean Square Error (RMSE), and Weighted Absolute Percentage Error (WAPE). In this study, the evaluation identified SARIMA as the suitable model for the available test data, although the same performance is not guaranteed for every client dataset.

**Record frequency.** The monthly, quarterly, or annual interval assigned to a financial record and used in organizing monitoring and forecasting activities.

**Seasonal Autoregressive Integrated Moving Average (SARIMA).** The statistical time-series model selected for the SafeBooks forecasting component based on the reported holdout evaluation. It represents non-seasonal and seasonal relationships in regularly spaced historical observations.

**SafeBooks.** The proposed web-based platform for managing client financial records, internal compliance-related schedules, descriptive analytics, forecasts, remarks, and printable reports. It does not perform official tax computation, filing, payment, or confirmation of BIR compliance.

**System Administrator.** The supporting user who reviews Bookkeeper registrations, approves or rejects account requests, manages account status, and reviews administrative activities recorded by the system.

**Taxpayer Identification Number (TIN).** The official taxpayer identifier recorded as part of a client profile. In SafeBooks, it may be used together with the client name to locate the appropriate record.

**Transaction details.** The individual entries recorded within a financial record, each containing a type, description, and amount.

**Web-based system.** A system accessed through a compatible web browser and connected to the configured network or hosting environment.
