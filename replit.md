# Overview

This is a comprehensive crypto trading bot system built as a SaaS platform offering arbitrage trading across multiple exchanges. The system supports multi-user subscriptions, advanced trading strategies, and real-time monitoring with Telegram notifications. It's designed to operate in simulation mode for demonstration while providing a foundation for real trading functionality.

# System Architecture

## Backend Architecture
- **Framework**: Flask-based Python application with SQLAlchemy ORM
- **Database**: PostgreSQL with automatic migration support via Flask-SQLAlchemy
- **Authentication**: Replit Auth integration with role-based permissions (USER, ADMIN, SUPER_ADMIN)
- **API Layer**: RESTful APIs with v2 optimization including caching and pagination

## Frontend Architecture
- **UI Framework**: Bootstrap 5 with dark theme optimization
- **Real-time Updates**: Optimized without WebSockets for better performance
- **Navigation**: Fast client-side navigation with auto-refresh capabilities
- **Charts**: Chart.js integration for analytics visualization

## Trading Engine Architecture
- **Multi-Exchange Support**: CCXT integration for Binance, Gate.io, MEXC, OKX, Bitget
- **Strategy Engine**: Modular design supporting arbitrage, scalping, grid trading, and pump/dump detection
- **Risk Management**: Position sizing, stop-loss, and daily loss limits
- **Simulation Mode**: Safe testing environment with realistic market data

# Key Components

## Trading Strategies (`advanced_strategies.py`)
- **Grid Trading**: Automated buy/sell orders at specific price levels
- **Scalping**: Micro-movement detection for rapid trades
- **Arbitrage**: Cross-exchange price difference detection
- **Momentum Trading**: Trend-following strategy implementation
- **Pump & Dump Detection**: Anomalous price movement identification

## SaaS Management (`saas_manager.py`)
- **Multi-tier Plans**: FREE ($0), BASIC ($29.99), PREMIUM ($99.99)
- **Feature Gating**: Trading limits, exchange access, and strategy availability per plan
- **Referral System**: Commission-based referral tracking (5-15% based on plan)
- **User Management**: Individual balances, settings, and trading limits

## Alert System (`advanced_alerts.py`)
- **Telegram Integration**: HTML-formatted notifications with configurable thresholds
- **Smart Filtering**: Duplicate prevention and priority-based alerting
- **Volume Alerts**: Unusual trading activity detection
- **System Monitoring**: Automated health checks and error notifications

## Performance Optimization (`performance_optimizer.py`)
- **Intelligent Caching**: 5-minute default timeout with configurable periods
- **Database Cleanup**: Automated removal of old trades and alerts
- **Query Optimization**: Indexed database queries with pagination
- **Memory Management**: Resource monitoring and cleanup routines

## Administrative Tools (`admin_manager.py`)
- **User Management**: Admin role assignment and permissions
- **License Management**: Subscription activation and monitoring
- **System Control**: Trading engine start/stop and configuration
- **Analytics**: User statistics and system performance metrics

# Data Flow

## Trading Flow
1. Market data collection from multiple exchanges via CCXT
2. Strategy execution with configurable parameters
3. Risk assessment and position validation
4. Trade execution (simulation mode) or order placement
5. Result logging and performance tracking
6. Alert generation for significant events

## User Interaction Flow
1. User authentication via Replit Auth
2. Plan-based feature access validation
3. Configuration management through web interface
4. Real-time dashboard updates via API polling
5. Notification delivery through multiple channels

## Data Processing Pipeline
1. Raw market data ingestion and validation
2. Strategy signal generation and filtering
3. Trade opportunity evaluation and ranking
4. Execution decision with risk management
5. Result storage and analytics processing

# External Dependencies

## Trading Infrastructure
- **CCXT Library**: Multi-exchange trading library via Node.js subprocess
- **Exchange APIs**: Direct integration with Binance, Gate.io, MEXC, OKX, Bitget
- **Market Data**: Real-time price feeds and order book data

## Communication Services
- **Telegram Bot API**: Real-time trading notifications and alerts
- **Email Services**: Account management and system notifications

## Development Tools
- **PostgreSQL**: Primary database with connection pooling
- **Bootstrap 5**: UI framework with dark theme support
- **Chart.js**: Real-time data visualization
- **Font Awesome**: Icon library for enhanced UI

# Deployment Strategy

## Production Environment
- **Runtime**: Python 3.11 with Node.js 20 for CCXT integration
- **Server**: Gunicorn WSGI server with auto-scaling support
- **Database**: PostgreSQL 16 with connection pooling and pre-ping
- **Process Management**: Parallel workflow execution for trading operations

## Configuration Management
- **Environment Variables**: Secure API key and credential storage
- **Database Configuration**: Automatic table creation and migration
- **Feature Flags**: Runtime configuration for trading modes and strategies

## Monitoring and Maintenance
- **System Health**: Automated performance monitoring and alerting
- **Error Handling**: Comprehensive logging with Telegram notifications
- **Data Cleanup**: Scheduled maintenance for database optimization
- **Performance Metrics**: Real-time system resource monitoring

# Changelog
- June 17, 2025. Initial setup

# User Preferences

Preferred communication style: Simple, everyday language.