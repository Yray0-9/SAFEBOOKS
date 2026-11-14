# CHAPTER 1

# INTRODUCTION

## Background of the Study

Managing financial records for several client businesses requires bookkeepers to
organize information, retrieve records, and review financial activity across
different periods. Research on small and medium-sized enterprises in Ghana
highlights the importance of business records management for decision-making and
business growth [1]. A study of web-based accounting also examined how online
processing can support bookkeeping activities [2]. These studies provide a basis for
using digital tools to organize financial information while retaining the
bookkeeper's responsibility for accurate recording and review.

In the Philippines, the Bureau of Internal Revenue (BIR) provides digital services
for taxpayer transactions. The Online Registration and Update System (ORUS) supports
taxpayer registration and the updating of registration information [3]. The BIR
Strategic Plan 2024-2028 also identifies digital transformation and improved
taxpayer services as priorities [4]. The present study focuses on the internal work
of bookkeepers who organize client information, maintain financial records, and
monitor record schedules in preparation for their professional responsibilities.

Within Davao del Norte, a study examined accounting information systems and
environmental uncertainty among agri-related cooperatives [5]. Another Philippine
study documented difficulties in maintaining accurate accounting records among micro
and small businesses in Zamboanga del Sur, including limitations in recording
practices and accounting knowledge [6]. These findings provide context for the
importance of organized bookkeeping information. For a bookkeeper managing several
clients, maintaining profiles, financial entries, schedules, and remarks across
separate files can complicate retrieval and review. A centralized workspace can
bring these related records together for easier access.

The present study focuses on the workflow of home-based bookkeepers associated with
the Bookkeepers Guild of Panabo City Inc. in Panabo City, Davao del Norte. Their
work involves maintaining information for several client businesses and reviewing
records by client and reporting period. The project addresses this workflow through
a shared structure for client profiles, financial entries, internal schedules,
summaries, and printable reports. Its contribution lies in organizing these
functions around the intended users' bookkeeping activities and providing historical
financial information for review and forecasting.

The study relates to the Commission on Higher Education's A.C.H.I.E.V.E. Agenda 2030
through its emphasis on SDG-based research and innovation [7]. It also relates to
the ICT Innovations priority of the Department of Science and Technology (DOST)
Harmonized National Research and Development Agenda 2022-2028 through its
application of web-based information management [8]. At the institutional level,
Davao del Norte State College's (DNSC) approved Research, Development, and Extension
(RDE) Agenda for 2026-2030 provides a framework for the College's research
priorities and extension programs [9]. The project's intended support for organized
bookkeeping work relates to Sustainable Development Goal 8, Decent Work and Economic
Growth [10]. Its application of digital technology to a local record-management
concern also relates to Sustainable Development Goal 9, Industry, Innovation and
Infrastructure [11].

To address this need, the study develops SafeBooks: A Web-Based Financial Records
and Compliance Monitoring System with Forecasting Analytics. The system provides
separate access for bookkeepers and administrators, maintains client profiles and
dated financial entries, and supports searching by client name or TIN. Bookkeepers
can record sales and expenses with separate coverage choices, encode tax-related
details and remarks, monitor internal schedules and deadlines, and prepare printable
client financial reports. Recorded amounts support descriptive summaries and financial trends, while forecasts
use the model selected through comparative evaluation when sufficient, regularly
spaced historical data are available.
SafeBooks does not calculate tax liabilities, file tax returns, process tax
payments, or confirm official BIR compliance.


**Objectives of the Study**
The primary objective of this study is to develop SafeBooks, a web-based
financial records monitoring system for home-based bookkeepers that centralizes
client records, supports internal schedule monitoring, and provides financial analytics with
an evaluated forecasting model for bookkeeping review and follow-up.
Specifically, the study aims to:
1. Digitize client business profiles, historical financial records, transaction
entries, record schedules, deadlines, remarks, and supporting notes.
2. Design and develop a centralized web-based workspace for maintaining
client profiles and related bookkeeping records, with search using the
client name or TIN.
3. Implement period-based financial records for manually encoded sales,
expenses, tax-related entries, deadlines, and notes, with separate monthly
or quarterly coverage for sales and expenses.
4. Compare Weighted Moving Average (WMA), Holt-Winters Exponential
Smoothing, and Seasonal Autoregressive Integrated Moving Average
(SARIMA) using a time-based holdout of historical client financial records
and the Mean Absolute Error (MAE), Mean Absolute Percentage Error
(MAPE), Root Mean Square Error (RMSE), and Weighted Absolute
Percentage Error (WAPE) metrics to determine a suitable forecasting
model.
5. Generate descriptive summaries and financial trends from recorded
financial data, and provide forecasts using the model selected through
comparative evaluation when sufficient, regularly spaced historical data
are available.
6. Generate dashboard and analytics outputs that provide financial
summaries, upcoming deadlines, client remarks, and forecasting results,
together with printable client financial reports for bookkeeping review and
follow-up.

**Significance of the Study**
The development of SafeBooks: A Web-Based Financial Records and
Compliance Monitoring with Forecasting Analytics. is expected to contribute to
improved financial record management, compliance monitoring, and digital
transformation of bookkeeping practices among its intended users.


**Home-Based Bookkeepers.** The primary beneficiaries of the proposed
system are home-based bookkeepers who manage multiple client businesses.
SafeBooks provides a centralized workspace for maintaining client profiles,
financial records, schedules, remarks, and supporting notes. Its search function
allows a bookkeeper to locate a client record using the client name or TIN.
Descriptive financial summaries and SARIMA forecasts provide additional
information for reviewing recorded financial activity and recognizing changes that
may require closer examination. These functions can lessen the need to move
between separate records and support a more consistent bookkeeping workflow.

**System Administrators.** System administrators can use tools to review
registrations, to approve or reject Bookkeeper accounts, manage the status of
accounts, and look at activities performed by users. Separate administrative
access allows to monitor Bookkeeper account activity.


**Client Businesses.** Client businesses might indirectly gain from a more
systematic manner by which their bookkeepers manage financial recordkeeping
and analysis. With the help of financial reports, predictions, and printables for
the client, it may be easier to relay their financial issues to the bookkeeper. By
utilizing these tools, they may expect a more uniform method of reviewing
records, while not hindering the professional accounting services and BIR
services.


**Bookkeepers Guild of Panabo City Inc.** The research may help the
company in knowing how a consolidated web-based platform can assist in
bookkeeping for several client companies. SafeBooks may give its members a
useful guide on how to manage the records of clients, examine summary
financial information, and oversee record schedules from one location. The study
may provide a basis for looking at a similar digital approach to bookkeeping in
the future.


**Scope and Limitation**
Home-based bookkeepers who are part of a bookkeepers' association
based in Panabo City in Davao del Norte are the primary users of SafeBooks.
Each Bookkeeper has a separate account through which they handle the profiles
and financial information of several client companies. The system also has a
System Administrator who checks various account registrations, decides on
application approvals or rejections, and monitors the use of the system by the
Bookkeepers.

SafeBooks is an web-based platform that was created using Python
programming language along with the Django framework for web development,
while the database is powered by PostgreSQL database management system.
Its user interface is developed using Django Templates, HTML, CSS, and
JavaScript so that it can be used through desktops and laptops. The email
integration makes sure that the user’s account is verified, given approval
notifications, and also warned via the email when an attempt has been made to
access their account. The two-factor authentication for System Administrator has
been ensured with the help of PyOTP framework.

The system retains information about Bookkeeper accounts, business
profiles of clients, TINs, details of businesses, records of finances, and any
necessary audit entries. It is understood that the records of finances may include
information about the number of transactions completed in the process of sales,
expenses and taxes, periods of time, due dates, and comments. Client profiles
may contain comments and other information useful for Bookkeepers.

The workflow starts with Bookkeeper’s registration and verification of
his/her email and the approval received from system administrators. Once getting
approval, Bookkeeper may keep client profiles, search for the client by means of
name or TIN, and make records of finance over a period of time.

The implementation, assessment, and expected use of SafeBooks apply
only to the specified home bookkeepers and their partner organization in Panabo
City, Davao del Norte. It is not made for governmental agencies, professional
accounting firms, big enterprises, or organizations outside the specific user
group. Furthermore, the customer enterprises turn out to be indirect beneficiaries
and are not given access to their individual accounts in the system.

The limitations of the platform are related only to the technology and
web-based environment utilized in this project. The software needs a standard
web-browser, a suitable device, and a network that has been set up correctly.
Additionally, there’s no use of AI, machine learning technologies, or blockchain
technologies.

The system won’t verify the inputted data independently against original
documents or relevant databases. For accurate predictive models, there should
be enough historical data that corresponds to the reporting frequency. Inaccurate
historical data may prevent the software from functioning as intended and affect
financial statements and forecasts issued by the software.

SafeBooks has been made to only offer services pertaining to internal
management of financial records, analytics, and schedule monitoring
compliance. The web application does not provide the option to calculate any tax
liabilities officially, submit tax returns, determine or confirm the official compliance
with the BIR regulations, or replace the standard bookkeeping and accounting
procedures. The current research considers the system exclusively based on its
functional, usability, and operating conditions which were meant for target users.
Formal cybersecurity certification, third-party security audit, large-scale
infrastructure testing, and enterprise-wide scalability assessment pertain to the
study's scope.

**Review of Related Literature and Works**
**Related Literature**

**Digital Financial Management and Manual Recordkeeping**

Web-based financial platforms provide combination of data storage,
overseeing and visual representations in a consolidated online world. A recent
study investigates systems that contain finances, dashboards and analytical
facilities without confining users to different monitoring tools. Besides, the same
study highlights that integrated platforms still have to overcome the issues
regarding privacy, scalability and value of the information [12]. These points give
a lot of food for thought when it comes to searching for the best platform although
it should not be presumed that digitalization will solve all finance management
problems on its own.

Although manual bookkeeping is a feasible option within limited contexts,
its shortfalls become more pronounced as the total number of records increases.
An assessment of PT Javindo Utama showed that recording mistakes were
common and that delays in the preparation of financial statements were evident
due to manual bookkeeping. Although these conclusions are probably true only
for PT Javindo Utama, they demonstrate that repeated manual process is
detrimental to the company that requires financial information on time [13]. In the
case of SafeBooks, this is sufficient to legitimize digital recordkeeping methods
rather than imply the elimination of responsibilities for the Bookkeeper in terms of
entering and checking the records accurately

**Web-Based Accounting and Client-Server Organization**

The use of online accounting systems has been investigated for their
capacity to enhance specific financial processes via a web interface. To illustrate,
a study has explored bank reconciliation and how an online accounting platform
could help carry out that process. Although SafeBooks does not perform bank
reconciliation, the study is relevant because it demonstrates how a defined 
accounting activity can be transferred from a manual arrangement to a
browser-accessible workflow [14]. The connection to the present study is
therefore the use of web technology for organized financial-record processing,
not the duplication of the study’s reconciliation function

A web-based platform also depends on the exchange of requests and
responses between the user interface and the server. Research on the
client-server model explains the roles of network communication and server
processing in delivering web-accessible functions [15]. This arrangement allows
the interface, application logic, and stored information to work together without
requiring the user to manage each technical component directly. SafeBooks
follows this general arrangement through a browser interface connected to a
Django application and its database.

**Financial Analytics and Forecasting**

Financial analytics adds value to stored records by organizing them into
summaries, trends, and other information that can be examined by the user. A
study involving management accountants and operational managers found that
business intelligence and analytics systems influenced how information was
produced, transmitted, and used during decision-related work. According to its
findings, the impact of analytics relied on the practices of the users with the
information instead of the technology itself[16]. SafeBooks illustrates such a
narrow role by giving descriptions of finances for Bookkeeper assessment rather
than making professional accounting conclusions and taking automated business
decisions.

Forecasting increases this process by predicting future values based on the
patterns derived from historical data. A large-scale forecasting research
compared statistical and machine learning methods, warning against believing
that more sophisticated models automatically provide better forecasts. The
current study supports the idea of assessing performance of forecasting methods
through the evaluation of errors and making a choice of a suitable approach
depending on the type of available data and goals of the forecasting process
[17]. In SafeBooks, SARIMA was chosen among the methods examined, and the
forecasts still depend on completeness, frequency, and seasonality of financial
data provided by the client.

**Web Application Environment and Philippine Digital Tax Services**

The organization of a web application affects how its interface, processing rules, and When it comes to web app architecture, the way the different components
work (like the interface, rules for processing, and data storage) is important. The
literature on multi-layer web applications considers the issue of distributing
functions between the presentation, application, and data layers of web
architecture, which allows organizing parts of the system properly and ensures
that the system is available via browser[18]. SafeBooks uses this scheme by
means of its web interface, Django processing, and PostgreSQL database.

Speaking about the Philippines, the Bureau of Internal Revenue (BIR) of
the country utilizes the electronic platforms to facilitate taxpayer operations. The
official documents state that the eFPS and eBIRForms are the electronic means
of filing returns, while the eFPS is capable of making electronic payments for the
eligible taxpayers as well[19]. It is worth mentioning that these platforms are
intended for the filing of taxes and making payments only, and they are not aimed
at the storing of information about businesses that are the ongoing clients of
these facilities.

**Synthesis and Research Gap**

The literature deals with a number of issues that influence the evolution of
SafeBooks: the transition from manual to electronic recordkeeping, the use of
web-based bookkeeping technology, the structure and function of web
applications, and the analysis of stored data with the aid of analytical tools,
including predictive modelling. All the sources deal with a specific context, for
example, general financial software, the manual accounting of one company, the
reconciliation of bank accounts, enterprise-level analytics, or government
taxation services. Though the materials in question indeed demonstrate valuable
recommendations, the audience, aims, and scope of application are different
from those of this paper. Thus, the existing research does not examine a
combination of the ideas outlined in the previous sources in the context of
everyday work by home-based accountants providing services to different
businesses.


The literature being reviewed is missing some information about how
accountants who work from home handle the financial data of different
businesses using only one internal process. The literature discusses some
individual issues involving electronic data, online processing, analysis, etc.
However, it does not consider their usage altogether in relation to bookkeeping.
SafeBooks fills the gap by linking the operations of record processing, financial
monitoring per period, internal schedule processing, and report generation on
one platform. It works distinctly from official procedures of tax calculation, filing,
payment, and compliance confirmation. Therefore, the originality of the study is in
adapting existing methods according to the specific needs of the users it is
targeted at.


**Related Works**

The programs which were analyzed include QuickBooks Online, Xero and
Taxumo. Their accounting processes and abilities to manage clients as well as
tax functions were helpful for the work of SafeBooks. The author describes their
relevance, while admitting that there are differences in their purpose and target
audience.

**QuickBooks Online**

QuickBooks Online Accountant enables accounting firms to work on different
clients at once and keep records of accounting and generate financial reports. It
relates to SafeBooks because of the organization and review of the financial data
for multiple clients. However, unlike this larger commercial platform, SafeBooks is
limited to the internal workflow established for employed home-based
bookkeepers that were studied.

**Xero**

Xero offers accountants an opportunity to gain a consolidated perspective of the
client data as well as financial ratios (receivables, payables, balances etc.). It
connects with SafeBooks in a shared internet-based environment where the
accountants can check data on various clients. Xero is concerned with broader
business accounting needs while SafeBooks provides limited monitoring and
auditing features for specific bookkeeping processes.

**Taxumo**

Taxumo enhances compliance related to taxes in the Philippines through online
services including computation, filing, payment, income and expense record
keeping and generation of books of account. In comparison, while both services
deal with tax-related aspects of finance, SafeBooks only helps users organize
internal records and manage schedules. It does not help with tax calculation,
return filing and payment.

**Table 1.** Comparison table of existing system vs. the proposed system.
(Well I cannot show the image unless you want it.)

In Table 1, we can see a summary of the functions that are discussed
throughout the rest of the paper. QuickBooks Online and Xero provide a wider
range of features in accounting, while Taxumo is concerned mainly with tax
functions. SafeBooks incorporates selected functions such as record
management, monitoring, analysis, and reporting into the designated workflow.

**Definition of Terms**

**Bookkeeper.** This is the primary person who manages information about clients,
keeps records related to the finances for a specific period, as well as makes
summaries and forecasts.

**Client profile.** It is a record of client’s identity, business and contact data. It links
the client with relevant bookkeeping records and notes made by Bookkeeper.

**Client remarks.** They are classifications that help to differentiate clients as New,
Active, Separated or Closed as per their status in bookkeeping relations.

**Compliance-related schedule monitoring.** The tracking module controls the
frequency of records and deadlines to look for records of clients that may need
help. However, its activity does not guarantee that reporting and BIR compliance
is fulfilled.

**Descriptive analytics.** The component of the approach responsible for
producing financial summaries along with expense, sales, and taxation reports
based on the captured historical input. The component describes the types of
records available but does not perform forecasting.

**Financial record.** A record that contains information specific to a particular
client for a specific time period. It consists of the date of the entry and the
frequency of recordings while also presenting additional notes about the
operations, details about transactions made, summarized results achieved, or
deadlines if relevant.

**Forecasting.**  Estimating the possible future financial values based on historical
data obtained from operations recorded for a client. The goal of forecasting is to
help the client but the results cannot be guaranteed.

**Forecasting model evaluation.** The time-based holdout methodology is used
for evaluating the performance of forecasting methods based on Mean Absolute
Error (MAE), Mean Absolute Percent Error (MAPE), Root Mean Square Error
(RMSE), and Weighted Absolute Percent Error (WAPE). The study proved that
the preferred model for the actual available data is SARIMA, but its effectiveness
cannot be guaranteed for every dataset from a specific client.

**Record frequency.** The monthly, quarterly, or annual interval assigned to a financial record and used in organizing monitoring and forecasting activities.

**SafeBooks.** The web-based approach to managing the records of clients related
to internal audit planning, analytics, forecasts, comments, and reports. The goal
of the approach is not computational tax calculations or confirming compliance
with BIR.

**System Administrator.** Supporting user that is responsible for monitoring the
activities of Bookkeeper, acceptance or rejection of account requests, account
status management, and evaluation of the administrative activities performed by
the system.

**Taxpayer Identification Number (TIN).** This is a unique identifier of the
taxpayer used in the client’s profile.TIN may be combined with the name of the
client in SafeBooks to find the desired record

**Transaction details.** Any entry made in the financial record containing the type
of transaction, description of it, and the sum of the transaction.

**Web-based system.** This refers to a system that is available on the web through
a compatible web browser, and that is linked with the established network.

**Seasonal Autoregressive Integrated Moving Average (SARIMA).** This is a
time series statistical model that is adopted by SafeBooks forecasting module,
based on the results of the holdout evaluation and that captures both seasonal
and non-seasonal relationships in the observed time series data.

