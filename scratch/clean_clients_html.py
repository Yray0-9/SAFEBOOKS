with open("templates/base/clients.html", "r", encoding="utf-8") as f:
    text = f.read()

# Fix the duplicate header inserted inside input tag
duplicate_header = """<input type="search" id="clientsSearchInput" placeholder="Search by client name or TIN" autocomplete="off">
{% extends 'base/bookkeeper_base.html' %}
{% load static %}

{% block page_title %}Clients{% endblock %}
{% block body_class %}clients-page{% endblock %}
{% block page_heading %}Clients{% endblock %}
{% block page_subtitle %}
<p class="dashboard-page-subtitle">Client directory and records access</p>
{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/reports.css' %}">
<link rel="stylesheet" href="{% static 'css/clients.css' %}?v=1.0">
{% endblock %}

{% block skeleton %}
<div class="skeleton-overlay dashboard-skeleton" id="pageSkeleton" aria-hidden="true">
    <div class="skeleton-shell">
        <div class="dash-sk-layout">
            <aside class="dash-sk-sidebar">
                <div class="skeleton-shimmer dash-sk-logo"></div>
                <div class="dash-sk-nav">
                    <div class="skeleton-shimmer dash-sk-nav-item"></div>
                    <div class="skeleton-shimmer dash-sk-nav-item"></div>
                    <div class="skeleton-shimmer dash-sk-nav-item"></div>
                    <div class="skeleton-shimmer dash-sk-nav-item"></div>
                    <div class="skeleton-shimmer dash-sk-nav-item"></div>
                    <div class="skeleton-shimmer dash-sk-nav-item"></div>
                </div>
            </aside>
            <section class="dash-sk-main">
                <div class="dash-sk-topbar">
                    <div class="skeleton-shimmer dash-sk-title"></div>
                    <div class="skeleton-shimmer dash-sk-search"></div>
                    <div class="skeleton-shimmer dash-sk-profile"></div>
                </div>
                <div class="dash-sk-content">
                    <div class="dash-sk-left">
                        <div class="dash-sk-card">
                            <div class="skeleton-shimmer dash-sk-card-head"></div>
                            <div class="dash-sk-table-row">
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                            </div>
                            <div class="dash-sk-table-row">
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                            </div>
                            <div class="dash-sk-table-row">
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                                <span class="skeleton-shimmer"></span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </div>
</div>
{% endblock %}

{% block content %}
<section class="dashboard-content">
    <article class="dashboard-card dashboard-fade-up clients-action-card clients-delay-05">
        <div class="clients-action-bar">
            <label class="dashboard-table-search clients-page-search" aria-label="Search clients by name or TIN">
                <i class="bi bi-search"></i>
                <input type="search" id="clientsSearchInput" placeholder="Search by client name or TIN" autocomplete="off">
            </label>"""

target_replacement = """<input type="search" id="clientsSearchInput" placeholder="Search by client name or TIN" autocomplete="off">
            </label>"""

if duplicate_header in text:
    text = text.replace(duplicate_header, target_replacement)
    print("Fixed duplicate header block!")
else:
    print("Header pattern not matched directly, checking normalized...")

with open("templates/base/clients.html", "w", encoding="utf-8") as f:
    f.write(text)
