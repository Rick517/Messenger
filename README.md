# Messenger - Real-time Chat Application

**A scalable, Telegram-inspired chat app for real-time communication, built for learning and production use.**

[![Status](https://img.shields.io/badge/status-production--ready-brightgreen)](https://github.com/your-repo/messenger)

Messenger is a comprehensive chat application enabling real-time communication between users. Originally an educational project, it has grown into a robust, production-ready system with over 6,500 lines of code and dozens of integrated technologies.

## Key Features

- **User Authentication**: Security with PyJWT tokens, Google OAuth2 integration, and email verification
- **Real-time Messaging**: Message delivery and updates via WebSockets (Flask-SocketIO)
- **Contact Management**: Add friends by email, search existing contacts, manage connections
- **Message Operations**: Copy, delete, and forward messages
- **Profile Management**: Edit profile information and avatars
- **Responsive Design**: Intuitive UI across devices

## Architecture & Technology Decisions

### Backend Structure

The structure of application isn't of the best quality. The code including API design should be more modular, coupled less closely and use more design principles.

Organization:

- **Routes**: Organized into main routes and people-specific endpoints
- **Models**: SQLAlchemy models for user data persistence
- **Forms**: Flask-WTF form handling for data validation
- **Utilities**: Shared helper functions and business logic

### Multi-Database Approach

A deliberate decision was made to utilize specialized databases for different data types:

1. **MongoDB**: Document store for chat histories and messages

   - Rationale: Flexible schema for varying message types, better scaling for chat operations
   - Implementation: Separate collections for group and contact chats

2. **SQLAlchemy (SQLite)**: Relational storage for user profiles and structured data

   - Rationale: Strong data integrity for user relationships and profile information
   - Implementation: User models with relationships to other entities

3. **Redis**: In-memory cache for ephemeral data
   - Rationale: High-speed access for session data, tokens, and real-time state
   - Implementation: Stores temporary authentication tokens and session information

### Authentication Flow

- JWT token-based sessions with refresh/access token pattern
- Google OAuth2 integration for social login
- Email verification for account security
- Token expiration (15min access / 30day refresh) for enhanced security

## Challenges

- **Poor Code Design**: Tight coupling in API routes and lack of modular patterns (e.g., no clear separation of concerns).
- **WebSocket Scalability**: Limited to single-server WebSocket connections, risking bottlenecks under high load.
- **Lack of Testing**: No unit or integration tests, increasing risk of regressions.
