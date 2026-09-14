# SAFEBOOKS: A WEB-BASED FINANCIAL RECORDS AND COMPLIANCE MONITORING SYSTEM WITH FORECASTING ANALYTICS

# CHAPTER 2

# METHODOLOGY

This chapter presents the methodology used to develop SafeBooks: A Web-Based Financial Records and Compliance Monitoring System with Forecasting Analytics. It describes the activities undertaken to define the requirements, design and implement the platform, verify its functions, and prepare it for use by its intended users. The methodology also establishes how revisions identified during development and testing were addressed before proceeding with the succeeding activities.

The study adopted the Modified Waterfall Model under the System Development Life Cycle (SDLC). This model follows an organized sequence while allowing the proponents to return to an earlier phase when a requirement, design decision, or system function needs revision [21]. As shown in Figure 1, the development process covers Planning, Requirements Analysis, System Design, Development and Implementation, Testing and Deployment, and Maintenance. This structure provided a clear progression of activities without treating the output of each phase as unchangeable.
(Attached image at the chatbox)

**Figure 1.** Modified Waterfall Model


**System Planning**

The system planning phase established the problem to be addressed, the intended users, and the boundaries of SafeBooks. The proponents identified home-based bookkeepers as the primary users and the System Administrator as the supporting user responsible for account oversight. The objectives and initial development activities were then organized around the management of multiple client records, internal schedule monitoring, financial review, and report preparation. These decisions provided the basis for the requirements examined in the next phase.

The project was planned in response to the difficulty of organizing financial information and compliance-related schedules for several client businesses through separate or manually maintained records. SafeBooks was therefore defined as a web-based platform that connects client profiles, period-based financial records, descriptive analytics, SARIMA forecasts, remarks, and printable reports within one internal workflow. The platform was planned as an internal record-management environment rather than a replacement for government tax services. Its boundaries exclude official tax calculation, return filing, tax payment processing, and confirmation of BIR compliance.


**Project Team Organization**

The project development team consisted of three proponents assigned as Systems Analyst, System Developer, and Documentarian, as shown in Figure 2. Each proponent had a primary area of responsibility while coordinating decisions involving the requirements, implementation, and documentation of SafeBooks. The partner organization and Project Adviser supported the project through operational input and academic guidance but are not included in the organizational chart.

(attached image at the chatbox)

**Figure 2.** Project Team Organization

**Roles and Responsibilities**

**Partner Organization: Bookkeepers Guild of Panabo City Inc.** The organization provided the practical context for understanding how bookkeepers manage financial information for multiple client businesses. Its input helped the proponents identify concerns involving record organization, retrieval, and compliance-related schedule monitoring. The proponents remained responsible for translating these concerns into system requirements and development decisions.

**Project Adviser: Lady Ben Roselle D. Nalzaro.** The Project Adviser provided academic guidance and reviewed the manuscript and system deliverables at different stages of the project. She recommended revisions concerning the scope, methodology, design, implementation, and presentation of the study. Her guidance helped the proponents address concerns and maintain consistency with the academic requirements of the Capstone Project.

**Systems Analyst: Jose Agbas.** The Systems Analyst identified and organized the functional and non-functional requirements of SafeBooks. The role involved translating the identified bookkeeping concerns into system workflows, data requirements, and user interactions. The Systems Analyst also checked whether the proposed design and implemented functions remained consistent with the objectives and scope of the study.

**System Developer: Romulo Magos.** The System Developer implemented the user interface, application functions, and database operations of SafeBooks according to the approved requirements and design. The role included integrating the authentication, client-management, financial-record, analytics, forecasting, monitoring, and reporting modules. The System Developer also corrected identified defects and verified that the connected modules operated as intended.

**Documentarian: Jandrie Daro.** The Documentarian prepared and maintained the research manuscript, system documentation, progress records, and other required project materials. The role included organizing revisions and checking that the written descriptions, figures, tables, and references reflected the current scope and implementation of SafeBooks. The Documentarian also reviewed the consistency, grammar, and formatting of the documents before submission.


**Work Breakdown Structure (WBS)**

Figure 3 presents the Work Breakdown Structure, which divides the SafeBooks project into smaller and manageable activities. Its six major divisions correspond to Planning, Requirements Analysis, System Design, Development and Implementation, Testing and Deployment, and Maintenance. Within each phase, the required work is separated into specific tasks that contribute to the development of the system.

The WBS served as a guide for organizing project activities and monitoring their progress. It helped the proponents connect individual tasks with the objectives and expected output of each development phase. Since the Modified Waterfall Model permits revisions, unfinished or revised work could also be traced to the phase in which further action was required.
(attached image at the chatbox)

**Figure 3.** Work Breakdown Structure (WBS)


**Gantt Chart**

Figure 4 presents the planned schedule for the phases identified in the Work Breakdown Structure. It shows the start and end dates allotted to Planning, Requirements Analysis, System Design, Development and Implementation, Testing and Deployment, and Maintenance. The timeline begins on February 28, 2026, and ends on December 20, 2026, allowing the duration and sequence of the phases to be viewed across the monthly schedule.

The Gantt chart served as a reference for organizing activities and monitoring progress against the target dates. It helped the proponents coordinate the work assigned to each development phase and identify activities that required follow-up or adjustment. Revisions encountered during development or testing could therefore be considered without losing track of the overall project schedule.
(attached image at the chatbox)

**Figure 4.** Gantt Chart


**System Analysis**

The system analysis phase examined the bookkeeping concerns identified during planning and translated them into functional and non-functional requirements. It defined the responsibilities and interactions of the Bookkeeper and System Administrator, together with the data needed for client profiles, financial records, internal schedule monitoring, analytics, forecasting, and reports. The proponents also identified the operational boundaries that separate SafeBooks from official tax calculation, filing, payment, and confirmation of BIR compliance. The results of this phase provided the basis for the system models and detailed requirements presented in the succeeding sections.


**System Architecture**
SafeBooks uses a three-tier, web-based architecture composed of presentation, application, and data layers. This arrangement separates the user interface, processing rules, and data-management responsibilities of the platform [22]. Figure 5 presents the proposed deployment of these layers through a browser interface, a Django application hosted on Render, and a relational database. The structure supports the functions assigned to the Bookkeeper and System Administrator without exposing the database directly to either user.

The presentation layer consists of the web browser through which the Bookkeeper and System Administrator access their authorized functions. Pages created with Django templates, HTML, CSS, and JavaScript display forms, dashboards, financial information, analytics, reports, and account-management options. Requests from the browser pass through the Render public endpoint using an HTTPS connection. The endpoint directs the requests to the web service and returns the processed pages or data through the same client-server exchange [23].

The application layer is hosted as a Render Web Service running one Django application. Its routes, views, service modules, and models manage authentication, account approval, client profiles, financial records, internal schedule monitoring, descriptive analytics, SARIMA forecasting, settings, audit logs, and reports. Authentication, role-based access, sessions, CSRF protection, and validation remain within the Django application and are applied before the requested function is processed. The application also uses Gmail SMTP to send account-related and security email messages.

The data layer stores the related information for user accounts, client profiles, reporting periods, financial records, transaction details, settings, and audit logs. Render PostgreSQL is identified as the database for the proposed deployment environment. SQLite remains limited to local development and is not used at the same time as the deployment database. The Django Object-Relational Mapper connects the application to the database when stored information is read or updated.
(attached image from the Chatbox)

**Figure 5.** System Architecture

During operation, the user sends a request through the browser and the Render public endpoint forwards it to the Django application. The application checks the session, assigned role, submitted data, and requested action before accessing the required function and database records. Financial summaries and forecasts are produced from the stored client information and transaction details when requested. The resulting page or data is then returned to the browser through the same secured path.


**Conceptual Framework**

The conceptual framework presents how information entered into SafeBooks moves through its main operations and produces records and analytical results for the Bookkeeper. Figure 6 organizes this relationship into input, process, and output components. The inputs consist of account and client information, period-based financial records and transaction details, reporting frequency, internal deadline dates, remarks, and system settings. These data are handled through authentication and account approval, client and financial record management, validation, internal schedule monitoring, descriptive analytics, SARIMA forecasting, report preparation, and audit logging.
(attached image at the chatbox)

**Figure 6.** SafeBooks Conceptual Framework (IPO Model)

These processes produce organized client profiles and financial records, internal schedule-monitoring results, financial summaries, descriptive analytics, SARIMA forecasts, printable reports, and audit records. The outputs help the Bookkeeper review a client’s recorded information and prepare internal reports from the same set of data. They also allow the System Administrator to oversee user accounts and review system activities within the assigned role. The framework does not represent official tax calculation, filing, payment, or confirmation of BIR compliance.


**Functional and Non-Functional Requirements**

SafeBooks supports client profile management, financial record management, internal schedule monitoring, descriptive analytics, forecasting, reporting, and administrative account oversight. The Bookkeeper can maintain client information, record period-based financial data, review summaries, monitor internal deadlines, and prepare reports through the assigned interfaces. Each financial record contains transaction details, a reporting frequency, an entry date, optional notes and deadline information, and a calculated total. Search by client name or TIN supports record retrieval without being treated as the main contribution of the system.

The non-functional requirements describe the expected quality of SafeBooks in terms of functional suitability, performance efficiency, compatibility, usability, reliability, security, maintainability, and portability. These attributes provide the basis for evaluating how well the implemented functions operate under normal use. The platform uses authenticated and role-based access, validates submitted information, and limits each Bookkeeper to the assigned client and financial records. Its web-based and modular structure also supports consistent browser access, testing, maintenance, and deployment.

**Functional Requirements**

1. Provide user authentication, email verification, session management, optional two-factor authentication, and administrator approval for Bookkeeper accounts.
2. Allow the System Administrator to approve, reject, deactivate, and reactivate Bookkeeper accounts and review related account activities.
3. Allow the Bookkeeper to create and maintain client profiles containing the client name, TIN, trade name, location, permit information, contact details, and remarks.
4. Validate required client information and email formats and prevent the use of a duplicate TIN.
5. Record monthly, quarterly, and annual financial information with an entry date, transaction details, notes, an optional internal deadline date, and a calculated total.
6. Monitor internal deadline information and indicate the remaining time or completion state based on the financial records entered for the client.
7. Enable the Bookkeeper to search and filter client information by client name or TIN in the appropriate client and analytics views.
8. Present dashboard information for client records, recent financial activity, client remarks, internal deadlines, and recorded financial totals.
9. Generate descriptive summaries and SARIMA forecasts from recorded sales, expenses, and tax-related amounts when sufficient, regularly spaced historical observations are available.
10. Produce printable client reports for selected reporting ranges and maintain role-appropriate audit records of important system activities.

**Non-Functional Requirements**

1. Functional Suitability: The system provides the functions required for client profile management, financial record management, internal schedule monitoring, descriptive analytics, SARIMA forecasting, reporting, audit review, and administrative account management. These functions support the assigned activities of the Bookkeeper and System Administrator within the defined scope of SafeBooks.
2. Performance Efficiency: The system processes submitted records, searches client information, displays dashboards and analytics, and prepares reports within a practical response time during normal use. Its database queries and application services are organized to avoid unnecessary processing when retrieving information for an authorized user.
3. Compatibility: The system operates through commonly used desktop and laptop web browsers while maintaining its intended functions and readable interface. Users can access SafeBooks without installing a separate desktop application, browser extension, or specialized hardware.
4. Usability: The system provides clear navigation, organized dashboards, consistent page layouts, understandable labels, and validation messages. These elements help the Bookkeeper and System Administrator complete assigned tasks and correct incomplete or invalid entries.
5. Reliability: The system maintains consistent operation during client management, financial record entry, internal schedule monitoring, analytics review, and report preparation. Validation and database controls help preserve submitted information and calculated totals during normal operation.
6. Security: The system protects accounts and financial information through authenticated login, email verification, administrator approval, role-based access, session controls, and optional two-factor authentication. It also restricts Bookkeepers to their assigned records and records important activities in the appropriate audit logs.
7. Maintainability: The system uses an organized Django project structure, separated service modules, database models, migrations, and ORM-based data access. This structure supports testing, troubleshooting, corrections, and later improvements without requiring the entire application to be rewritten.
8. Portability: The system can operate in compatible web environments that support Python and Django. SQLite supports local development, while PostgreSQL is configured for the proposed Render deployment without changing the core functions of SafeBooks.


**Use Case Diagram**

The Use Case Diagram, shown in Figure 7, identifies the interactions available to the Bookkeeper and System Administrator within SafeBooks. The system boundary separates the functions performed through the platform from the two external user roles. The Bookkeeper manages client profiles, financial records, internal deadlines, analytics, forecasts, reports, and account settings. The System Administrator reviews registrations, manages Bookkeeper accounts, monitors administrative information, maintains system settings, and reviews audit activities.
(attached image at the chatbox)

**Figure 7.** Use Case Diagram

Both roles log in before accessing the functions assigned to them and may manage their respective profile and security settings. The Bookkeeper can search for a client by name or TIN, review dashboard information, maintain transaction details, monitor internal deadline information, and prepare printable reports. The System Administrator can approve or reject registrations, manage account status and deactivation requests, review the administrative dashboard, and maintain system-wide settings. Role-based access prevents either user from performing functions that are not assigned to the account.


**Context Flow Diagram**

The Context Flow Diagram, shown in Figure 8, treats SafeBooks as a single process and shows the information exchanged with its external entities. The Bookkeeper and System Administrator remain outside the system boundary because they provide data to the platform and receive information based on their assigned roles. Each labeled arrow represents information entering or leaving SafeBooks rather than the internal steps used to process it. This level of detail keeps the diagram focused on the system’s external interactions.
(attached image at the chatbox)

**Figure 8.** SafeBooks Level 0 Context Flow Diagram

The Bookkeeper submits login credentials, client profile information, financial record and internal deadline data, report parameters, and profile or security updates. SafeBooks returns authentication and account information, client and financial record information, dashboard and deadline summaries, analytics and forecast results, printable reports, and role-appropriate activity information. The System Administrator submits login credentials, registration and account decisions, deactivation-request decisions, and system or security updates, while receiving authentication results, Bookkeeper account information, administrative metrics, pending-request information, settings, and audit records. No data flow is shown between SafeBooks and the Bureau of Internal Revenue because the platform does not perform official tax filing, payment, or compliance confirmation.


**Level 1 Data Flow Diagram**

The Level 1 Data Flow Diagram, shown in Figure 9, expands SafeBooks into the processes that handle information received from the Bookkeeper and System Administrator. The inputs and outputs identified in the Context Flow Diagram are distributed among authentication, client management, financial record management, dashboards and analytics, reporting, account administration, settings, and audit review. D1 is identified as the SafeBooks Database because it represents the single logical data store used by these processes. It contains user accounts, client profiles, reporting periods, financial records, transaction details, settings, deactivation requests, and audit records.
(attached image at the chatbox)

**Figure 9.** Level 1 Data Flow Diagram

Bookkeeper information passes through the appropriate processes before being stored or returned as client records, deadline summaries, analytics, SARIMA forecasts, printable reports, or activity information. Administrator decisions update Bookkeeper accounts, deactivation requests, and system settings, while the corresponding account information and metrics are returned to the System Administrator. Each process exchanges only the data required for its responsibility and communicates with the data store instead of allowing either user to access it directly. The flows remain within the scope of SafeBooks and do not represent official BIR filing, payment, or compliance confirmation.

**System Design**

The System Design section describes how the identified requirements are translated into user interactions, application processes, and data structures. SafeBooks organizes its functions around authentication and account management, client profiles, financial records, internal schedule monitoring, descriptive analytics, SARIMA forecasting, reporting, audit review, and administrative oversight. The design reflects the assigned activities of the Bookkeeper and System Administrator from account access and record maintenance to analysis and report preparation. These functions operate within one connected web application rather than as independently deployed services.

The design also defines the database structure, data relationships, and validation controls used to maintain organized bookkeeping information. Key considerations include unique TIN enforcement, required-field validation, reporting periods and frequencies, transaction details, optional internal deadlines, secure access, and role-based data restrictions. These controls support consistent record processing and prevent either user from accessing information outside the assigned role. The design remains within the project scope and does not provide official tax calculation, filing, payment, or confirmation of BIR compliance.

**Entity Relationship Diagram (ERD)**

The Entity Relationship Diagram, shown in Figure 10, identifies the core data entities used by SafeBooks and the relationships that connect them. The structure supports account administration, client profiles, reporting periods, financial records, transaction details, internal deadline monitoring, workspace settings, deactivation requests, and audit activities. Primary and foreign keys maintain the links between related records while preserving the ownership assigned to the Bookkeeper and System Administrator. The diagram presents the principal database fields needed to explain these relationships without treating application functions as separate entities.
(attached image at the chatbox)

**Figure 10.** Entity Relationship Diagram (ERD)

An AdminAccount may approve Bookkeeper accounts, review deactivation requests, and create administrative audit records. Each BookkeeperAccount owns its client profiles, financial records, workspace defaults, deactivation requests, and activity records. A Client is connected to its reporting periods and financial records, while each FinancialRecord belongs to one period and contains one or more transaction details. These relationships allow SafeBooks to retrieve connected information without giving either user direct access to records outside the assigned role.

**Data Dictionary**

The data dictionary summarizes the SafeBooks database tables and their attributes. It provides a clear reference for field names, data types, and key roles used across the system.

**Table 2. List of SafeBooks Database Tables**
(attached image at the chatbox)

**Table 3. List of SafeBooks Database Tables**
(attached image at the chatbox)

**Technologies, Concepts, and Theories**

This section discusses the technologies, concepts, and analytical procedures considered in the development of SafeBooks. It explains how financial information is collected, validated, stored, summarized, and prepared for forecasting. It also describes the model-evaluation procedure used to select the forecasting method intended for later integration into the platform.

**Financial Data Collection**
SafeBooks obtains its financial information from records manually entered by an authorized Bookkeeper. The collected information includes client business details, reporting periods, transaction details for sales, expenses, and tax-related amounts, record frequencies, optional deadlines, and notes. Required information is entered through structured forms rather than gathered automatically from source documents or BIR systems. Centralized digital collection supports more organized access to bookkeeping information than records maintained across separate files or paper documents [24].

The submitted information is stored in related database tables according to the Bookkeeper, client, reporting period, and financial record to which it belongs. This arrangement supports client retrieval, period-based monitoring, analytics, forecasting preparation, and report generation from the same set of stored records. The accuracy of these outputs still depends on the completeness and correctness of the information entered by the Bookkeeper.

**Financial Data Processing**
Before accepting submitted information, SafeBooks checks required fields, numerical formats, permitted values, record ownership, and other applicable input rules. Client profiles are also checked for duplicate TIN values, while financial records must be linked to valid clients and reporting periods. These validation procedures reduce incomplete or inconsistent entries but do not independently establish whether the encoded information agrees with official documents [25]. The Bookkeeper therefore remains responsible for reviewing the source information and correcting identified encoding errors.

After validation, the platform stores the accepted records and calculates the totals needed for dashboards, financial summaries, trend views, and printable reports. Period and frequency information organizes the records for monthly, quarterly, or annual review, while optional deadline dates support internal schedule monitoring. The same prepared historical values form the input for descriptive analytics and the forecasting procedure when sufficient observations are available.

**Descriptive Financial Analytics**
SafeBooks uses descriptive financial analytics to organize recorded information into summaries, comparisons, and trend views. Descriptive analytics examines available historical data to show what has been recorded during the selected periods rather than determining the cause of a financial change or prescribing a business decision [26]. The platform summarizes sales, expenses, tax-related amounts, and resulting net values from the Bookkeeper's entries. These results are displayed through dashboards, client-level views, and printable reports.

This approach was selected because it presents the stored financial information in a form that can be reviewed within the Bookkeeper's existing workflow. It allows the user to compare periods and identify values that may require closer examination without presenting the result as an official accounting conclusion. The descriptive outputs remain separate from the forecasting estimates discussed in the succeeding subsection.

**Forecasting Analytics Using Evaluated Statistical Forecasting Models**
Forecasting analytics estimates possible future values from the sequence of previously recorded financial observations. Three statistical time-series models were evaluated for SafeBooks: Weighted Moving Average (WMA), Holt-Winters Exponential Smoothing, and Seasonal Autoregressive Integrated Moving Average (SARIMA). WMA assigns greater influence to selected recent observations, Holt-Winters represents level, trend, and seasonal behavior through exponential smoothing, and SARIMA models non-seasonal and seasonal relationships within a time series. The comparison was conducted to identify a model for subsequent integration rather than to assume that one method would perform best in every dataset.

The models were evaluated through a time-based holdout procedure. Historical financial records from 2023 and 2024 formed the training set, while the corresponding 2025 records were reserved as the test set and were excluded during model fitting. Forecasts for the test period were then compared with the actual recorded values for 2025. Keeping the test observations separate from model fitting provides a more appropriate assessment of performance on unseen time-ordered data [27].

The comparison used Mean Absolute Error (MAE), Mean Absolute Percentage Error (MAPE), Root Mean Square Error (RMSE), and Weighted Absolute Percentage Error (WAPE). MAE represents the average absolute error, MAPE expresses the average error as a percentage, and RMSE gives greater influence to larger errors. WAPE expresses the total absolute error relative to the total actual value and was also used to derive a presentation value labeled as accuracy:

**WAPE-based Accuracy = 100% − WAPE**

This accuracy value is a transformation of WAPE and not a separate forecasting metric. Lower MAE, MAPE, RMSE, and WAPE values indicate smaller forecast errors, while a higher WAPE-based accuracy indicates a smaller aggregate error relative to the actual values.

**Table 4. Comparative Evaluation of Forecasting Models**
(attached image at the chatbox)

As shown in Table 4, SARIMA produced the lowest MAE, MAPE, RMSE, and WAPE among the three models under the reported evaluation. Its WAPE of 6.06% corresponds to a WAPE-based accuracy of 93.94%. Holt-Winters ranked next with a WAPE-based accuracy of 93.06%, while WMA obtained 72.10%. Based on these holdout results, SARIMA was selected for subsequent integration into the SafeBooks forecasting component, subject to the amount and regularity of the available client data.

SARIMA extends the ARIMA approach by combining non-seasonal and seasonal components, allowing recurring patterns at a defined interval to be represented [28]. Its general notation is:

**SARIMA (p, d, q)(P, D, Q)<sub>s</sub>**

In this notation, *p*, *d*, and *q* are the non-seasonal autoregressive, differencing, and moving-average orders; *P*, *D*, and *Q* are their seasonal counterparts; and *s* is the number of observations in one seasonal cycle.

For this evaluation, the specification SARIMA (0,1,0)(0,1,0)<sub>s</sub> was used because the available training history was limited. A seasonal period of 12 represented regularly spaced monthly sales observations, while a seasonal period of 4 represented regularly spaced quarterly expense and tax-related observations. These settings allow the model to account for recurrence according to the frequency of the evaluated records. Forecasting will be made available only when a client has enough consistently spaced historical observations for the required model configuration.

**Emerging Web Technologies**
SafeBooks was developed with Django, PostgreSQL, HTML, CSS, JavaScript, and Bootstrap. Django provides the server-side structure for routing, authentication, validation, application rules, and database access [29]. PostgreSQL is identified as the relational database for deployment, while SQLite remains limited to local development. HTML, CSS, JavaScript, and Bootstrap provide the structure, appearance, and interactive behavior of the browser interfaces.

The proposed deployment uses a Render Web Service, Render PostgreSQL, an HTTPS endpoint, and Gmail SMTP for account-related email delivery. Responsive layout practices support consistent use within the desktop and laptop browser environment covered by the study. Together, these technologies allow the presentation, application, and data components of SafeBooks to operate as one connected web platform.


**Technologies Used in the System**

**Visual Studio Code (VS Code)**
Visual Studio Code served as the primary code editor during the development of SafeBooks. It provided one workspace for organizing the Python and Django source files, HTML templates, style sheets, JavaScript files, tests, and project configuration. Its integrated terminal, source navigation, and debugging support assisted the proponents in implementing and checking connected frontend and backend functions.

HTML and CSS defined the structure and appearance of the browser interfaces, while JavaScript handled interactive page behavior. Bootstrap supported consistent layouts, navigation elements, forms, modal windows, and interface feedback across the Bookkeeper and System Administrator views. Django handled URL routing, request processing, authentication, application rules, and database access for the web platform.
(attached image at the chatbox)

**Figure 12.** Visual Studio Code (VS Code)

**PostgreSQL Database Management System**
PostgreSQL serves as the relational Database Management System for the configured SafeBooks environment and is identified as the database for the proposed Render deployment. It stores the related account, client, period, financial record, transaction detail, settings, deactivation-request, and audit data described in the data dictionary. Primary keys, foreign keys, unique constraints, and Django migrations help maintain the structure and consistency of these records. SQLite remains available for local development and is not used simultaneously with PostgreSQL in the same configured environment.
(attached image at the chatbox)

**Figure 13.** PostgreSQL Database Management System 


**System Testing and Implementation**

This section describes the proposed testing and implementation procedures for determining whether SafeBooks operates according to its functional and non-functional requirements. Testing covers authentication, account administration, client profiles, financial records, internal deadlines, analytics, SARIMA forecasting, reporting, settings, and audit activities. Implementation includes preparing the deployment environment, applying the database migrations and configuration, and checking the connected functions before the platform is made available to its intended users.

**System Test Plan**

The proponents will use Black Box Testing to evaluate SafeBooks through the inputs submitted by the users and the outputs returned by the platform. The procedure checks the visible behavior of each function without requiring the tester to examine the internal source code. This approach allows the test cases to be compared directly with the functional requirements and expected results.

The test cases cover account access, registration decisions, client-profile validation, period-based financial records, transaction details, internal deadline monitoring, dashboards, analytics, forecasts, reports, role restrictions, and audit logs. Valid, incomplete, duplicate, unauthorized, and out-of-range inputs will be used where applicable. The observed result of each test will be compared with the expected behavior before the test case is marked as passed or failed.

Testing will also check whether calculated totals, descriptive summaries, SARIMA results, and printable reports remain consistent with the stored financial information. Forecasting tests will include sufficient-data and insufficient-data conditions, the applicable seasonal frequency, and comparison of generated estimates with the expected calculation results. Required-field validation, duplicate-TIN prevention, account-status restrictions, session controls, and Bookkeeper data isolation will also be verified. After deployment configuration, the proponents will perform a basic operational check of authentication, database access, static resources, email delivery, and the main Bookkeeper and System Administrator workflows.

**Table 5. Proposed System Testing Plan for SafeBooks**
(attached image at the Chatbox)


**System Implementation Plan**

**Environment Configuration and Database Setup**
Implementation will begin by configuring the Render Web Service and the environment variables required by the Django application. Render PostgreSQL will serve as the deployment database, while SQLite will remain limited to local development. Django migrations will be used to create and update the database tables and their relationships without manually rebuilding the schema. Database connectivity, static resources, HTTPS access, and Gmail SMTP email delivery will be checked before the system is released to its intended users.

**Module Integration and Verification**
SafeBooks will be deployed as one Django web application, with its connected modules verified in a planned sequence. Authentication, email verification, account approval, and role-based access will be checked first to confirm that only authorized Bookkeepers and the System Administrator can use their assigned functions. Verification will then cover client profiles, financial records and transaction details, internal deadline monitoring, dashboards, analytics, SARIMA forecasting, printable reports, settings, deactivation requests, and audit logs. Relevant tests will be repeated after integration to confirm that stored data, calculated results, and access restrictions remain consistent across the system.

**Production Deployment and User Evaluation** 
After configuration and testing, SafeBooks will be made available through its secured Render web endpoint to selected Bookkeepers affiliated with the Bookkeepers Guild of Panabo City Inc. and the designated System Administrator. User accounts and assigned access rights will be confirmed before the participants begin the evaluation. The proponents will use a structured questionnaire based on the approved functional and non-functional requirements to assess whether the system performs its intended tasks and is suitable for the users' bookkeeping workflow. The results and reported issues will guide necessary revisions before the final release of the project.

**Monitoring and Maintenance**
Following deployment and evaluation, the proponents will monitor application logs, database connectivity, audit records, and issues reported by users. Confirmed errors will be corrected, while required security, dependency, and configuration updates will be applied when necessary. Affected functions will be retested before each correction or update is released to reduce the risk of disrupting existing workflows. Maintenance decisions will remain within the approved project scope and will consider the findings gathered during system testing and user evaluation.


**System Maintenance**

System maintenance will cover corrective, adaptive, and preventive work after SafeBooks has been deployed and evaluated. Confirmed errors will be documented and corrected, while changes to the hosting environment, dependencies, security configuration, and database schema will be applied when required. Affected functions and data relationships will be retested before an update is released to the users. Application logs, audit records, and user feedback will help the proponents prioritize maintenance without extending the system beyond its approved scope.


**Systems Security Plan**

The Systems Security Plan defines the controls used to protect SafeBooks accounts, client information, financial records, and audit data from unauthorized access or modification.

**Authentication and Authorization**
SafeBooks uses separate access rules for the Bookkeeper and System Administrator through authenticated application sessions. A Bookkeeper can manage only the clients and financial records associated with that Bookkeeper's account, while the System Administrator is limited to account administration, system settings, and audit-related functions. Account approval, account-status checks, password protection, email verification, and optional two-factor authentication provide additional controls before protected functions can be accessed. Recorded activities are associated with the authenticated account to support accountability and review.

**Data Transmission and Privacy Protection**
The proposed Render deployment will use an HTTPS endpoint to encrypt data exchanged between the user's browser and the Django application. This protection applies to login details, Taxpayer Identification Numbers, client profiles, financial records, and other information submitted through the system. Database and email credentials will be supplied through protected environment variables rather than displayed in the interface or included in the manuscript. Access to the deployed PostgreSQL database will be limited to the configured application connection and authorized maintenance activities.

**Application and Database Security**
SafeBooks uses Django's security middleware, session controls, server-side validation, and Cross-Site Request Forgery protection for requests that modify stored information. Django's Object-Relational Mapping layer handles database operations through parameterized queries, reducing exposure to SQL injection when it is used correctly. Database constraints and application validation help enforce required fields, unique TIN values, valid relationships, and assigned record ownership. Security-related configuration and dependency updates will be tested before deployment to avoid weakening existing controls or disrupting authorized workflows.


**Systems Maintenance Plan**

The Systems Maintenance Plan outlines the post-deployment activities needed to preserve the reliability, security, and usability of SafeBooks. Maintenance will be initiated in response to confirmed system issues, hosting or dependency notices, changes to approved requirements, and feedback from the intended users. The plan covers database performance, software dependencies, analytics and schedule monitoring, and controlled system refinements.

**Database Optimization and Performance Management**
The proponents will review PostgreSQL connectivity, database growth, query performance, and the integrity of related records during maintenance. Indexes and frequently used queries may be examined when client, period, financial record, or audit data begins to affect response time. A database backup will be prepared before schema migrations or major corrective changes, and the affected records will be checked after the update. These activities will support reliable retrieval of client records by name or TIN as the database grows.

**Dependency and Framework Updates**
The Django framework, Python packages, and deployment configuration will be reviewed for supported updates and reported security issues. An available update will first be checked for compatibility with the SafeBooks codebase, PostgreSQL database, and Render environment rather than being installed automatically. Authentication, database access, email delivery, analytics, reports, and the main Bookkeeper and System Administrator workflows will be retested after a relevant update. The tested version will be deployed only when it does not introduce unresolved errors or weaken existing security controls.

**Analytics and Schedule-Monitoring Review**
The descriptive analytics, calculated totals, and SARIMA results will be checked when an inconsistency is reported or an approved requirement changes. Any correction to the calculation logic will be compared with the stored financial records and tested across the supported reporting frequencies before release. Internal deadline and schedule-monitoring fields may be adjusted when the approved bookkeeping workflow changes. These functions remain internal monitoring aids and will not calculate tax liabilities, file returns, or confirm official BIR compliance.

**Feature Iteration and User Feedback Integration**
Feedback from the designated System Administrator and participating Bookkeepers will be recorded and classified as an error, usability concern, or enhancement request. Confirmed concerns may guide corrections to interface layouts, financial record forms, reports, and other existing functions. Each accepted change will be tested before release and documented when it affects the approved requirements or user procedures. Requests that introduce functions outside the project scope will require separate review and approval before implementation.
