# SAFEBOOKS: A WEB-BASED FINANCIAL RECORDS AND COMPLIANCE MONITORING SYSTEM WITH FORECASTING ANALYTICS

# CHAPTER 2

# METHODOLOGY

This chapter discusses the methodology employed in the development of
SafeBooks: A Web-Based Bookkeeping Platform for Client Transaction Entry
Records with Financial Analytics and Forecasting Insights. The chapter describes
the systematic sequence of procedures that were adhered to in the process of
planning, analysis, design, development, testing, implementation, and
maintenance of the system for the provision of assistance to accounting

specialists in their implementation of bookkeeping and accounting activities.
The Modified Waterfall Model was chosen for this study as part of the
System Development Life Cycle (SDLC), due to its systematic and orderly
approach characteristic of projects where the requirements are already specified
[23]. This model goes through different phases including Planning, Requirements
Analysis, System Design, Development and Implementation, Testing and
Deployment, and Maintenance, as illustrated in Figure 1.

(If you want to see the image i will share it)

**Figure 1.** Modified Waterfall Model


**System Planning**

During the system planning step, the issue that needs to be resolved, the
intended users, and the limits of SafeBooks were determined. The supporters
recognized home-based bookkeepers as the main users and the System
Administrator as the assisting user who is in charge of monitoring the accounts in
the next phase of the design process. The plans were made with a view to
working on many client records, keeping track of internal schedules, revising
financial data, and preparing necessary reports by the team.

The objective of the project is to provide a solution for the problem of
managing financial data and compliance schedules for multiple businesses of
clients under separate or manually operated records. This is why the project
defines SafeBooks as a platform that integrates profiles of clients, periodic
financial records, descriptive data analytics, models of forecasts developed in
accordance with the selected model, and notes about the reports that can be
printed.The aim of the platform is thus to create an environment for internal
records management rather than replace a governmental tax service; the scope
excludes any activities related to taxation, including tax calculation, tax return, tax
payment, and BIR compliance confirmation.


**Project Team Organization**

The project development team was comprised of three individuals who
served as proponents in the roles of Systems Analyst, System Developer, and
Documentarian (as seen in Figure 2). Each member of the team performed
specific functions yet all were required to coordinate their choices regarding the
requirements, implementation, and documentation phases of SafeBooks. The
partner organization and Project Adviser provided support in the form of
operational expertise as well as theoretical knowledge but were not displayed in
the organizational chart.

(attached image at the chatbox)

**Figure 2.** Project Team Organization

**Roles and Responsibilities**

**Partner Organization: Bookkeepers Guild of Panabo City Inc.** The organization
gave a clear example of how accountants handle financial data for numerous
businesses run by various clients. The organization also made it possible for the
proponents to identify issues related to the process of keeping, retrieving, and
reporting records. The proponents had to make use of this information to outline
what system requirements they needed, as well as what developments they
needed to make.

**Project Adviser: Lady Ben Roselle D. Nalzaro.** The Project Adviser
gave academic supervision and checked the whole research paper and the project outcomes from time to time. This expert offered some corrections in terms
of the scope, methodology, project design, and presentation. Her assistance has
provided the authors with a possibility to answer the questions raised and meet
the academic criteria for a Capstone Project.

**Systems Analyst: Jose Agbas.** The Systems Analyst gathered and categorized the
functional and nonfunctional requirements of SafeBooks. Her job included
transforming the gathered information into business processes, data needs, and
use cases. The Systems Analyst proved that the adopted system design and the
implemented features were compliant with the goals and scope of the project.

**System Developer: Romulo Magos.** The System Developer provided the implementation of the
user interface and functionalities of SafeBooks according to project specification.
This position entailed creating the modules for identification, clients’
management, keeping financial records, analysis, forecast, and reporting. The
System Developer dealt with bugs fixing and checking whether all modules were
working appropriately.

**Documentarian: Jandrie Daro.**  The role of Documentarian was responsible for the
preparation and maintenance of research manuscript, system documentation,
progress records, and other required project materials. Responsibilities included
organizing revisions and verifying that the written descriptions, illustrations,
tables, and references are up-to-date with respect to the objectives and
implementation of SafeBooks. The Documentarian was responsible for checking
the consistency, style, and format of the documents prior to submission.


**Work Breakdown Structure (WBS)**

As depicted in Figure 3, Work Breakdown Structure breaks down
SafeBooks project into smaller activities. The major divisions in the Work
Breakdown Structure include Planning, Requirements Analysis, Systems Design,
Development and Implementation, Testing and Deployment, and Maintenance.
Each phase then further breaks down the required work into different tasks.

In essence, the Work Breakdown Structure has served as a basis for
organizing project activities and monitoring the work progress. In particular, the
Work Breakdown Structure allowed the developers to link the tasks to the goals
and desired outcomes of each project phase. Moreover, the Modified Waterfall
Model allows the project team to track activities that have not been completed or
have been revised.

(attached image at the chatbox)

**Figure 3.** Work Breakdown Structure (WBS)


**Gantt Chart**

In the provided figure 4, the anticipated plan for each phase defined in the
Work Breakdown Structure is shown. Several development stages such as
Planning, Requirements Analysis, System Design, Development and
Implementation, Testing, Deployment, and Maintenance are likely to start from
February 28, 2026, and finish by December 20, 2026.

The Gantt chart acted as an ideal tool which assisted in organizing
activities in an appropriate manner and to monitor progress with respect to the
planned dates and target milestones.

(attached image at the chatbox)

**Figure 4.** Gantt Chart


**System Analysis**

The phase of system analysis evaluated the accounting issues raised in
the phase of planning and converted those issues into functional or
non-functional requirements. This phase included determination of duties of the
Bookkeeper and System Administrator and the types of data needed in the
different functions of the system including client account details, accounts and
transaction data, control of internal scheduling, analytics and reporting. The
phase also covered clearly the operational limits of the system to distinguish
SafeBooks from computation, filing and payment tax duties and procedures of
BIR. The findings of the analysis also formed the base of future development of
the system


**System Architecture**
SafeBooks has a three-layer web-based architecture, which includes
presentation, application and data layers. The principle of three-layer architecture
allows for separating user interface, processing rules and responsibilities in terms
of data management of the system technology [24]. Figure (5) provides
information about the implementation of technologies of the system using
web-desktop interface, a Django application and relational database system. In accordance with this architecture possibilities are provided for fulfilling all
necessary duties by the Bookkeeper and System Administrator but there is no
risk of direct access to database by any of the users.

The function of the presentation layer encompasses the web browser
through which the users can fulfill all of their functions. Pages created with
Django templates, HTML, CSS, and JavaScript display forms, dashboards,
financial information, analytics, reports, and account-management options.
Requests from the browser pass through the Render public endpoint using an
HTTPS connection. The endpoint directs the requests to the web service and
returns the processed pages or data through the same client-server exchange
[25].


The application layer is hosted as a Render Web Service running one
Django application. Its routes, views, service modules, and models manage
authentication, account approval, client profiles, financial records, internal
schedule monitoring, descriptive analytics, SARIMA forecasting, settings, audit
logs, and reports. Authentication, role-based access, sessions, CSRF protection,
and validation remain within the Django application and are applied before the
requested function is processed. The application also uses Gmail SMTP to send
account-related and security email messages.

The data layer stores the related information for user accounts, client
profiles, reporting periods, financial records, transaction details, settings, and
audit logs. Render PostgreSQL is identified as the database for the proposed
deployment environment. SQLite remains limited to local development and is not
used at the same time as the deployment database. The Django
Object-Relational Mapper connects the application to the database when stored
information is read or updated.

(attached image from the Chatbox)

**Figure 5.** System Architecture

During operation, the user sends a request through the browser and the
Render public endpoint forwards it to the Django application. The application
checks the session, assigned role, submitted data, and requested action before
accessing the required function and database records. Financial summaries and
forecasts are produced from the stored client information and transaction details
when requested. The processed page or requested data is then securely sent
back to the user's browser through the same protected connection.


**Conceptual Framework**

The conceptual framework illustrates how data that is registered in
SafeBooks functions in its principal operations and generates records and
reports for the Bookkeeper. Figure 6 presents this interaction as input, process,
and output components. The inputs consist of information regarding accounts
and clients and all financial records and transactions over a specific time,
frequency of reporting, internal deadlines, and additional comments as well as
system settings. The input data undergoes the processes of authentication/approval of accounts, management of clients and financial
records, validation, internal scheduling, analytics, forecasting through the
selected model, report generation, and audit logging

(attached image at the chatbox)

**Figure 6.** SafeBooks Conceptual Framework (IPO Model)

The procedures lead to the formation of structured customer profiles as well
as records of finances, results of internal scheduling monitoring, reports, financial
review, and forecast results based on the chosen model, printed records, and
audit information. As such, the results allow the Bookkeeper to analyze a client’s
records and generate internal reports. In addition, the framework enables the
System Administrator to track user accounts and monitor system activities in the
given capacity. The framework is not a proper instrument for tax computation.


**Functional and Non-Functional Requirements**

SafeBooks supports client profile management, financial record
management, internal schedule monitoring, descriptive analytics, forecasting,
reporting, and administrative account oversight. The Bookkeeper can maintain
client information, record period-based financial data, review summaries, monitor internal deadlines, and prepare reports through the assigned interfaces. Each
financial record contains transaction details, a reporting frequency, an entry date,
optional notes and deadline information, and a calculated total. Search by client
name or TIN supports record retrieval without being treated as the main
contribution of the system.

Non-functional requirements are the specifications for the characteristics
desired by SafeBooks, such as performance effectiveness, efficiency,
compatibility, usability, reliability, security, maintainability, and portability of the
application. These requirements are the parameters for evaluating how the
functionalities are performed in practice. The application provides verified and
role-based access and verifies the inputs from users and prevents all
Bookkeepers from accessing the same client. Its web-based and modular
structure also supports consistent browser access, testing, maintenance, and
deployment.

**Functional Requirements**

1. Provide user 2FA authentication, email verification, session management,
two-factor authentication, and administrator approval for Bookkeeper
accounts.
2. Allow the System Administrator to approve, reject, deactivate, and
reactivate Bookkeeper accounts and review related account activities.
3. Allow the Bookkeeper to create and maintain client profiles containing the
client name, TIN, trade name, location, permit information, contact details,
and remarks.
4. Validate required client information and email formats and prevent the use
of a duplicate TIN.
5. Record monthly, quarterly, and annual financial information with an entry
date, transaction details, notes, an optional internal deadline date, and a
calculated total.
6. Monitor internal deadline information and indicate the remaining time or
completion state based on the financial records entered for the client.
7. Enable the Bookkeeper to search and filter client information by client
name or TIN in the appropriate client and analytics views.
8. Present dashboard information for client records, recent financial activity,
client remarks, internal deadlines, and recorded financial totals.
9. Generate descriptive summaries and SARIMA forecasts from recorded
sales, expenses, and tax-related amounts when sufficient, regularly
spaced historical observations are available.
10. Produce printable client reports for selected reporting ranges and maintain
role-appropriate audit records of important system activities.

**Non-Functional Requirements**

1. Functional Suitability: The system provides the functions required for client
profile management, financial record management, internal schedule
monitoring, descriptive analytics, SARIMA forecasting, reporting, audit
review, and administrative account management. These functions support
the assigned activities of the Bookkeeper and System Administrator within
the defined scope of SafeBooks.
2. Performance Efficiency: The system processes submitted records,
searches client information, displays dashboards and analytics, and
prepares reports within a practical response time during normal use. Its
database queries and application services are organized to avoid
unnecessary processing when retrieving information for an authorized
user.
3. Compatibility: The system operates through commonly used desktop and
laptop web browsers while maintaining its intended functions and readable
interface. Users can access SafeBooks without installing a separate
desktop application, browser extension, or specialized hardware.
4. Usability: The system provides clear navigation, organized dashboards,
consistent page layouts, understandable labels, and validation messages. These elements help the Bookkeeper and System Administrator complete
assigned tasks and correct incomplete or invalid entries.
5. Reliability: The system maintains consistent operation during client
management, financial record entry, internal schedule monitoring,
analytics review, and report preparation. Validation and database controls
help preserve submitted information and calculated totals during normal
operation.
6. Security: The system protects accounts and financial information through
authenticated login, email verification, administrator approval, role-based
access, session controls, and two-factor authentication. It also restricts
Bookkeepers to their assigned records and records important activities in
the appropriate audit logs.
7. Maintainability: The system uses an organized Django project structure,
separated service modules, database models, migrations, and
ORM-based data access. This structure supports testing, troubleshooting,
corrections, and later improvements without requiring the entire
application to be rewritten.
8. Portability: The system can operate in compatible web environments that
support Python and Django. SQLite supports local development, while
PostgreSQL is configured for the proposed Render deployment without
changing the core functions of SafeBooks.


**Use Case Diagram**

The Use Case Diagram, shown in Figure 7, identifies the main functions
available to the Bookkeeper and System Administrator in SafeBooks. The
Bookkeeper manages client profiles, searches for clients by name or TIN,
maintains financial records and internal deadlines, reviews analytics and
forecasts, generates printable reports, and examines personal activity records.
The System Administrator reviews Bookkeeper registrations and deactivation
requests, manages Bookkeeper accounts, views administrative information,
maintains system settings, and reviews audit records. Both actors can manage
their own profile and security settings through their respective accounts.
(attached image at the chatbox)

**Figure 7.** Use Case Diagram

Access to SafeBooks is limited to authenticated users, although
authentication is not represented as a main use case. The functions of each
actor remain separated according to the account’s assigned role. A deactivation
request is reviewed only after it has been submitted by a Bookkeeper, and the
resulting decision is handled through Bookkeeper account management. These
restrictions allow both actors to perform their responsibilities without accessing
functions assigned to the other role.

**Context Flow Diagram**

The Context Flow Diagram shown in Figure 8 considers SafeBooks as a
single process and indicates the information exchanged with external entities.
The Bookkeeper and the Systems Administrator can be found outside the system
boundary as they are the relevant providers of data to the system. Each arrow
contains a label and indicates the information that has been sent into or out of
SafeBooks. At this level of abstraction, the diagram shows the emphasis on
external interactions of the system.

(attached image at the chatbox)

**Figure 8.** SafeBooks Level 0 Context Flow Diagram

The Bookkeeper passes along the login information, the information about
the client profiles including financial records and deadlines, the report settings,
and data on any profile or security updates. SafeBooks replies with the
necessary authentication and account information, as well as the client and
financial records’ information, deadlines, and analytics and forecasts, printable
reports, and information on the functions available for the user. The System
Administrator sends login information, registration and deactivation requests, and
security updates by receiving the authentication messages, Bookkeeper account
information, administrative data, and audit information in return. There is no
information exchange between SafeBooks and the Bureau of Internal Revenue
since the latter is not responsible for tax filing, payments, and confirmations.



**Level 1 Data Flow Diagram**

The Level 1 Data Flow Diagram, shown in Figure 9, expands SafeBooks into the processes that The Level 1 Data Flow Diagram shown in Figure 9 divides SafeBooks into
six processes that handle the information identified in the Context Flow Diagram.
These processes cover authentication and account access; client, financial, and
deadline records; dashboards, analytics, forecasts, and reports; Bookkeeper
account administration; system settings; and activity or audit review. D1 is
identified as the SafeBooks Database because it represents the single logical
data store used by these processes. It contains user accounts, client profiles,
reporting periods, financial records, transaction details, settings, deactivation
requests, and audit records.

(attached image at the chatbox)

**Figure 9.** Level 1 Data Flow Diagram

Information submitted by the Bookkeeper passes through the appropriate
processes before it is stored or returned as client and financial information,
deadline summaries, analytics, forecasts, printable reports, or activity
information. Decisions made by the System Administrator update Bookkeeper
accounts, deactivation requests, and system settings, while administrative and
audit information is returned as needed. Each process exchanges only the
information required for its assigned function and accesses the SafeBooks
Database instead of allowing either actor to reach the data store directly. These
flows remain within SafeBooks and do not represent BIR tax filing, payment, or
compliance confirmation.

**System Design**

The System Design section explains how the specified requirements are
turned into user operations, application processes, and data structures. The
functions of SafeBooks are organized in accordance with authentication and
account management; maintenance of client profiles; work with financial
information; control over internal schedule; and data processing. In design, all
activities of the Bookkeeper and System Administrator connected with access to
accounts and keeping records, analysis, and making reports are reflected

The plan sets the framework for the database structure and the
connection of the data and the validation processes involved, so that the
recorded bookkeeping information is organized. Important considerations
include: TIN uniqueness enforcement, validation of required fields, reporting
periods and frequencies, transaction specifics, internal deadlines, secure system
access and restrictions based on the user's role. The aim of such procedures is
to execute records processing successfully while denying one user of using
information not intended for him/her. The design remains within the boundaries of
the project and does not include the provision of taxation calculation, payment,
filing and BIR compliance confirmation.

**Entity Relationship Diagram (ERD)**

The Entity Relationship Diagram, which can be found in Figure 10,
identifies the main data entities used by SafeBooks and their connections. The
structure provides for accounting operation management, client profile
management, reporting periods, transaction details, making sure the internal
deadlines are observed, creating settings for the workspace, requests for
deactivation, and auditing. The primary and foreign keys maintain the
connections between the records of data while preserving the information
administration assignments. The diagram shows the main database fields related
to presenting these records.

(attached image at the chatbox)

**Figure 10.** Entity Relationship Diagram (ERD)

Some functions of an AdminAccount include approving Bookkeeper
accounts, monitoring deactivation requests and forming login records for
administrative purposes. Every BookkeeperAccount is responsible for the client
profiles, financial information, workspace defaults and deactivation requests as
well as activity records of its clients. Moreover, a Client is associated with the
corresponding reporting periods and financial records, whereas each
FinancialRecord is related to one particular period and may have a number of
entries with transaction details. This provides SafeBooks with an opportunity of
obtaining complete information without granting any of the users direct access to
the records outside their assigned roles.

**JSON Schema Diagram**

As it is depicted in Figure 11, the JSON Schema Diagram presents the
structure and organization of the data used in the SafeBooks system. The
diagram shows how the data objects are interlinked and how the information is
transferred between various system functions. 

(attached image at the chatbox)
**Figure 11:** JSON Schema Diagram

The meaning of the diagram is that it serves as an aid in data organization
and validation, which guarantees proper information distribution and processing.


**Data Dictionary**

The data dictionary gives a short overview of the tables of the SafeBooks
database along with their features.

**Table 2. List of SafeBooks Database Tables**
(attached image at the chatbox)

**Table 3. List of SafeBooks Database Tables**
(attached image at the chatbox)

**Technologies, Concepts, and Theories**

This chapter presents the technological innovations, ideas and analytical
tools that supported the creation of SafeBooks. It reveals how financial
information is collected, verified, saved, summarized and applied for predictions.
Moreover, it describes the method of evaluation used for choosing the right
prediction model, the method that is planned to be integrated into the system
later.

**Financial Data Collection**
SafeBooks receives its financial data from reports filled in organization by
a registered bookkeeper. Information collected consists of data about clients’
businesses, time frames of reporting, information about the transaction including
sales, expenses and tax payments as well as frequency of information filling,
optional deadlines, notes and additional information. Required information is
manually provided through different forms instead of automatic collection from
primary documents or BIR systems. The centralized digital collection makes
bookkeeping systems more comprehendible than the systems that store
information in different files or in paper archives[26].

Information received is organized into separate tables in the database
where it is stored by the bookkeeper, customer, reporting period and financial record. Such arrangement allows for easy retrieval of data by client or time frame
monitoring, analysis and report generation. Although the effectiveness of the
outputs will depend on the accuracy and completeness of the information
provided by the bookkeeper.

**Financial Data Processing**
fields, numeric patterns, allowed values, record ownership status, and other
applied input rules. Information is also verified for duplicates of TIN in client
records, and financial entries are paired with valid clients and reporting periods.
Though this verification considerably minimizes the incidence of records that are
either incomplete or inconsistent, it does not ensure compliance between data
entered and official information [27]. This means that the job of the Bookkeeper is
still to check the source documents and correct encoding errors discovered.

After the verification of records occurred, the system saves the records
that are accepted and computes totals needed to create the dashboards,
financial summaries, and trend charts, as well as printable reports. Time and
frequency data serve to categorize records by the period of their monthly,
quarterly, or annual visualization while optional due dates facilitate internal
planning. The same historical data will be used for predictive analysis and
forecasting if the counts are sufficient.

**Descriptive Financial Analytics**
Descriptive financial analysis is used by SafeBooks to collate recorded
data into summaries, comparisons, and trend charts. Descriptive analysis is a
study of historical data that shows what happened rather than explaining how it
happened or what to do next [28]. The application summarizes sales, expenses,
taxes, and net values based on the recorded information.

This method was chosen due to its ability to show financial data in a way
that can be examined in accordance with the Bookkeeper's existing processes. It
enables a user to compare different periods and to find numbers that need extra
attention while keeping the outcome informal. The descriptive information is kept
separate from the forecasting information in a further part of the report.

**Forecasting Analytics Using Evaluated Statistical Forecasting Models**
SafeBooks utilizes forecasting techniques in estimating the future financial
performance based on previously input client data. In choosing the right
forecasting strategy, three statistical approaches were assessed – Weighted
Moving Average (WMA), Holt-Winters Exponential Smoothing, and Seasonal
Autoregressive Integrated Moving Average (SARIMA). These approaches involve
different techniques of forecasting including weighted averaging of actual
observations, exponential smoothing of level, trend, and seasonal components,
and modeling seasonal/non-seasonal relationships in time series.

The models were evaluated using the time-wise holdout method. The
historical data for 2023 and 2024 formed the training set whereas the observed
data for 2025 served as the test set and were not used for fitting. The predicted
figures for the test period were compared with the actual values obtained in
2025. It is believed that keeping the test data away from fitting results in better
performance evaluation in unseen time series data [29].

The comparison used Mean Absolute Error (MAE), Mean Absolute
Percentage Error (MAPE), Root Mean Square Error (RMSE), and Weighted
Absolute Percentage Error (WAPE). MAE represents the average absolute error,
MAPE expresses the average error as a percentage, and RMSE gives greater
influence to larger errors. WAPE expresses the total absolute error relative to the
total actual value and was also used to derive a presentation value labeled as
accuracy:

**WAPE-based Accuracy = 100% − WAPE**

This accuracy value is a transformation of WAPE and not a separate forecasting
metric. Lower MAE, MAPE, RMSE, and WAPE values indicate smaller forecast
errors, while a higher WAPE-based accuracy indicates a smaller aggregate error
relative to the actual values

**Table 4. Comparative Evaluation of Forecasting Models**
(attached image at the chatbox)

As shown in Table 4, SARIMA produced the lowest MAE, MAPE, RMSE,
and WAPE among the three models under the reported evaluation. Its WAPE of
6.06% corresponds to a WAPE-based accuracy of 93.94%. Holt-Winters ranked
next with a WAPE-based accuracy of 93.06%, while WMA obtained 72.10%.
Based on these holdout results, SARIMA was selected for subsequent
integration into the SafeBooks forecasting component, subject to the amount and
regularity of the available client data.

SARIMA extends the ARIMA approach by combining non-seasonal and
seasonal components, allowing recurring patterns at a defined interval to be
represented [30]. Its general notation is:

**SARIMA (p, d, q)(P, D, Q)<sub>s</sub>**

In this notation, *p*, *d*, and *q* are the non-seasonal autoregressive,
differencing, and moving-average orders; *P*, *D*, and *Q* are their seasonal
counterparts; and *s* is the number of observations in one seasonal cycle.

For this evaluation, the specification SARIMA (0,1,0)(0,1,0)<sub>s</sub>
was used because the available training history was limited. A seasonal period of
12 represented regularly spaced monthly sales observations, while a seasonal period of 4 represented regularly spaced quarterly expense and tax-related
observations. These settings allow the model to account for recurrence according
to the frequency of the evaluated records. Forecasting will be made available
only when a client has enough consistently spaced historical observations for the
required model configuration.

**Emerging Web Technologies**
SafeBooks was developed with Django, PostgreSQL, HTML, CSS,
JavaScript, and Bootstrap. Django provides the server-side structure for routing,
authentication, validation, application rules, and database access [31].
PostgreSQL is identified as the relational database for deployment, while SQLite
remains limited to local development. HTML, CSS, JavaScript, and Bootstrap
provide the structure, appearance, and interactive behavior of the browser
interfaces.

The proposed deployment uses a Render Web Service, Render
PostgreSQL, an HTTPS endpoint, and Gmail SMTP for account-related email
delivery. Responsive layout practices support consistent use within the desktop
and laptop browser environment covered by the study. Together, these
technologies allow the presentation, application, and data components of
SafeBooks to operate as one connected web platform.


**Technologies Used in the System**

**Visual Studio Code (VS Code)**
Visual Studio Code served as the primary code editor during the
development of SafeBooks. It provided one workspace for organizing the Python
and Django source files, HTML templates, style sheets, JavaScript files, tests,
and project configuration. Its integrated terminal, source navigation, and
debugging support assisted the proponents in implementing and checking
connected frontend and backend functions.

HTML and CSS defined the structure and appearance of the browser
interfaces, while JavaScript handled interactive page behavior. Bootstrap
supported consistent layouts, navigation elements, forms, modal windows, and
interface feedback across the Bookkeeper and System Administrator views.
Django handled URL routing, request processing, authentication, application
rules, and database access for the web platform
(attached image at the chatbox)

**Figure 12.** Visual Studio Code (VS Code)

**PostgreSQL Database Management System**
PostgreSQL serves as the relational Database Management System for
the configured SafeBooks environment and is identified as the database for the
proposed Render deployment. It stores the related account, client, period,
financial record, transaction detail, settings, deactivation-request, and audit data
described in the data dictionary. Primary keys, foreign keys, unique constraints,
and Django migrations help maintain the structure and consistency of these
records. SQLite remains available for local development and is not used
simultaneously with PostgreSQL in the same configured environment.

(attached image at the chatbox)

**Figure 13.** PostgreSQL Database Management System 


**System Testing and Implementation**

This section describes the proposed testing and implementation
procedures for determining whether SafeBooks operates according to its
functional and non-functional requirements. Testing covers authentication,
account administration, client profiles, financial records, internal deadlines,
analytics, SARIMA forecasting, reporting, settings, and audit activities.
Implementation includes preparing the deployment environment, applying the
database migrations and configuration, and checking the connected functions
before the platform is made available to its intended users.

**System Test Plan**

The promoters are going to use Black Box Testing to assess SafeBooks
based on the information put into the system by users and the outputs the
platform provides. The method evaluates the observable behavior of the
functions without requiring the person carrying out the test to look at the internal
source code. This way it becomes possible to compare the test cases directly
with the functional requirements and the expected outcomes.

Test cases cover everything from information access via account, to
registering decisions and client profile verification, and to financial documents by
period, transactions and time deadlines, dashboards, and analytics. Types of input
we will test for include proper and incomplete entries, duplicate or unauthorized and
too-advanced documents, among other types. We will be comparing our test results
and the responses we saw.

The testing will also include confirmation of the accuracy of total
computations, summary statistics, SARIMA calculation results, and printed report
outputs in comparison with stored financial data. Forecasting tests will include
both the sufficient data conditions and the insufficient data conditions, applicable
seasonal frequency and comparison of the results with expected calculations. It
will also check for required field validation, duplicate Tax Identification Number
inhibition, account status restrictions, session rules, and the isolation of
Bookkeeper information. Following the configuration, the authors will perform
operational checks on the aspects of authentication, database access, available
resources, email processing, and the defined Bookkeeper and System
Administrator functioning.

**Table 5. Proposed System Testing Plan for SafeBooks**
(attached image at the Chatbox)


**System Implementation Plan**

**Environment Configuration and Database Setup**
The first step in implementation is to set up the Render Web Service and
the necessary variables in the Django app. The only database we will deploy on
Render PostgreSQL while using SQLite locally for development purposes.
Django migrations will take care of the creation and modification of all database
tables and relationships automatically. Once done, tests related to database
connection, static resources, HTTPS support, and the Gmail SMTP delivery will
be performed.

**Module Integration and Verification**
SafeBooks will remain as a Django web application along with its
interconnected modules that will have to be tested sequentially. Testing will start
from Authentication, email verification, account approval, and access control
confirming that the relevant user groups, namely Bookkeepers and the System
Admin, can carry out their assigned functions only. Testing will go on to include
client details, financial records, and Transaction details, tracking deadlines,
dashboards, analytics, SARIMA forecasting, prints, settings, deactivation
requests, and audit logs therefore. The relevant tests will be repeated after the
integration stage to ensure the stability of the stored data

**Production Deployment and User Evaluation** 
Upon completion of the configuration and testing process, SafeBooks will
be accessible via the secured Render online platform to chosen Bookkeepers
who are part of the Bookkeepers Guild of Panabo City Inc. as well as the
appointed System Administrator. User accounts and their respective access
rights will be verified before the user testing begins. A structured questionnaire
will be used to measure the effectiveness of the software in carrying out its
intended functions and suitability for the users bookkeeping processes. The
findings obtained during this testing phase will help refine the project further.

**Monitoring and Maintenance**
After the implementation has been carried out and results have been
analyzed, the project team will keep track of the logs of the program, database
connections, audit records, and errors reported by the users. Errors that have
been identified will be amended, and also necessary updates to security,
dependencies, and configurations will be undertaken as needed. Disturbed
functions will be checked again prior to the release of any updates to minimize
the disruptions caused to existing processes. Maintenance decisions will be
executed accordingly to the project terms and will take into account the results of
the testing and evaluation of the system by the users.


**System Maintenance**

System maintenance involves making fixes, improvements, and repairs
after SafeBooks has been set up and tested. Errors that have been confirmed will
be recorded and fixed, while changes to the hosting environment, dependencies,
security configuration, and database schema will be made when necessary. The
functions of the system and the relationships between its data will be checked
again before the new version is released to the customers. In order to carry out
maintenance properly, it will be based on the application logs, audit records, and
feedback on the application usage


**Systems Security Plan**

The Systems Security Plan defines the controls used to protect SafeBooks
accounts, client information, financial records, and audit data from unauthorized
access or modification.

**Authentication and Authorization**
Separate access rules are used by SafeBooks for Bookkeeper and
System Administrator considering the authenticated sessions of the application.
The Bookkeeper manages the clients and financial records of the respective Bookkeeper only. The activities can be performed by the System Administrator
regarding the account management, settings of the system, and the checks on
audit related tasks. The control checks include the approval of the account,
checking on status of the account, protecting of the password, verifying the
email, and the authentication of the procedure in cases where the access to the
protected facilities is concerned. The actions being taken are related to the use of
the logged-in account.

**Data Transmission and Privacy Protection**
The proposed Render deployment will incorporate an HTTPS endpoint
that will encrypt data transmitted between the user's web browser and the Django
application. This means that the login information, Taxpayer Identification
Number, client profile, financial records, and all other data sent through the
system will be protected. In the database and email system, the credentials will
be supplied as secure environment variables so they will not be displayed
through the user interface or be included in written documentation. Access to the
deployed PostgreSQL database will only be possible through the configured
application connection and authorized maintenance.

**Application and Database Security**
SafeBooks implements some of Django’s securities, such as its
middleware, its session management, its validation procedures, and its protection
from Cross-Site Request Forgery for all requests that impact data in its system.
The Object-Relational Mapping of Django employs prepared statements to
execute database commands while minimizing susceptibility to SQL injection.
Various data constraints and application-level validations ensure proper
recording of the information entered by the user including mandatory fields,
unique TIN, valid relation types and identification of the owner of the record.
Before deploying any security settings and updating dependencies, SafeBooks
will rigorously test their security settings to protect against any possibility of
hindering the ongoing security mechanisms.


**Systems Maintenance Plan**

The Systems Maintenance Plan describes the activities necessary for
maintaining SafeBooks’ effectiveness, integrity, and usability after its deployment.
Maintenance will begin only in the presence of actual problems occurring in the
system, notices regarding hosting or dependencies, changes in the set
requirements, or comments from the target users. It includes database
performance, software dependencies, analytics and scheduling, as well as
system improvements.

**Database Optimization and Performance Management**
During maintenance, the supporters will analyze the connection of
PostgreSQL, database expansion, efficiency of queries, and the reliability of
relevant records. Indexing and the most commonly used queries will be assessed
when how long a customer has been in business, when they were last regards,
and the record of accounts starts to affect timing. Prior to modifying the schema
in any major way, database backup has to be done, and the records being
influenced must be verified. These activities are meant to ensure safe access to
client records by name or TIN as their number increases in the database.

**Dependency and Framework Updates**
An evaluation of Django framework, Python packages, and deployment
settings will be made for updates and security issues. Updates will then be
verified for compatibility with the codesource of SafeBooks, PostgreSQL
database, and Render environment instead of applying the update automatically.
Subsequent to applying the update, authentication, database access, email,
analytics, and functionalities of Bookkeeper and System Administrator will be
tested. The newly applied version will only be released once confirmed that it
does not have any bugs nor any security flaws.

**Analytics and Schedule-Monitoring Review**
Any report of discrepancy, inconsistency in totals or problems with
SARIMA results will prompt verification of descriptive analytics calculations,
totals, and results. Any updates of calculation logic will be compared against
existing storage of financial records and ensured to work properly at the various
frequencies before being released. Internal deadlines and schedules can be
changed when the updated approved accounting workflow is implemented.
These functions will remain only internal monitoring mechanisms and will not
calculate any tax liabilities and submit returns to BIR

**Feature Iteration and User Feedback Integration**
After production is put into motion, user reviews of both system
administrators and the independent accountants belonging to the Bookkeepers
Guild of Panabo City Inc. will be collected to aid in making improvements to
future versions of the software. The feedback will enable the developers to fix
interface layout, improve the forms used for entering financial records, and add
new types of dashboard visualization. The parameters of the feedback process
would allow adjustments to the platform that would meet current workflow
requirements of the local accountants perfectly     
