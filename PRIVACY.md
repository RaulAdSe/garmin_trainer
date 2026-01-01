# Privacy Policy - Garmin Training Insights

**Last Updated:** 2025-12-30

This document describes how the Garmin Training Insights application collects, stores, processes, and shares your health and fitness data.

---

## 1. Health Data Collected

The application collects the following categories of health and fitness data from your Garmin Connect and Strava accounts:

### 1.1 Personal Profile Information
- **Demographic data:** Age, gender, weight (kg)
- **Physiological metrics:** Maximum heart rate, resting heart rate, lactate threshold heart rate

### 1.2 Heart Rate Data
- Average and maximum heart rate per workout
- Heart rate zone distribution (Zone 1-5 percentages)
- Heart rate reserve calculations

### 1.3 Training Metrics
- **Fitness indicators:** CTL (Chronic Training Load), ATL (Acute Training Load), TSB (Training Stress Balance)
- **Risk assessment:** ACWR (Acute:Chronic Workload Ratio), risk zone classification
- **Load metrics:** HRSS (Heart Rate Stress Score), TRIMP
- **Power metrics (cycling):** FTP, normalized power, TSS, intensity factor, variability index
- **Swim metrics:** CSS (Critical Swim Speed), SWOLF scores by stroke

### 1.4 Workout History
- Activity type (running, cycling, swimming)
- Duration and distance
- Pace/speed data
- Cadence
- Elevation gain
- Activity timestamps
- Workout names and notes

### 1.5 Fitness Level Data (from Garmin)
- VO2max estimates (running and cycling)
- Fitness age
- Training status (productive, maintaining, detraining, etc.)
- Training readiness score and level
- Race predictions (5K, 10K, Half Marathon, Marathon)

### 1.6 Daily Activity Data
- Step counts
- Active minutes

### 1.7 Race Goals
- Target distances
- Target finish times
- Race dates

---

## 2. Data Storage

### 2.1 Local Database Storage
All collected data is stored locally in SQLite database files:
- `training.db` - Primary training data storage
- Contains: activity metrics, fitness metrics, user profiles, race goals, weekly summaries, Garmin fitness data, workout analyses

### 2.2 Credential Storage
- **Garmin Connect credentials:** Email and password are encrypted using Fernet (AES-128-CBC) symmetric encryption before storage
- **Encryption key:** Stored in environment variable `CREDENTIAL_ENCRYPTION_KEY`
- **Strava OAuth tokens:** Access and refresh tokens are stored in the database (Note: encryption recommended before production deployment)

### 2.3 File Permissions
Database files should be secured with restricted permissions (`chmod 600`) to prevent unauthorized access.

---

## 3. Third-Party Data Sharing

### 3.1 OpenAI API Integration
This application uses OpenAI's API for AI-powered training analysis and coaching. The following data is transmitted to OpenAI:

#### Data Categories Sent to OpenAI:

**Personal Metrics:**
- Age
- Gender

**Heart Rate Data:**
- Maximum heart rate
- Resting heart rate
- Lactate threshold heart rate
- HR zone boundaries (calculated from above)

**Training Metrics:**
- CTL (Chronic Training Load)
- ATL (Acute Training Load)
- TSB (Training Stress Balance)
- ACWR (Acute:Chronic Workload Ratio)
- Risk zone classification
- Readiness score and zone
- Daily activity (steps, active minutes)

**Workout History:**
- Recent workout details (last 7 days)
- Activity type, duration, distance
- Average/max heart rate
- Pace and training load metrics
- Zone distribution

**Race Goals:**
- Target distances
- Target times
- Race dates
- Training paces derived from goals

**Fitness Level:**
- VO2max (running and cycling)
- Training status
- Race predictions from Garmin

### 3.2 Data Handling by OpenAI
- Data is transmitted over HTTPS (encrypted in transit)
- Review OpenAI's data usage policies at: https://openai.com/policies/privacy-policy
- OpenAI API requests are subject to their data retention and usage policies
- Consider enabling zero data retention options if available

### 3.3 Other Third-Party Services
- **Garmin Connect:** Used for data synchronization (your Garmin account credentials)
- **Strava:** Optional integration for additional activity data (OAuth tokens)
- **Stripe:** Payment processing for subscriptions (if enabled)

---

## 4. User Rights

### 4.1 Data Export
You can export your data in the following formats:
- **FIT files:** Export individual workouts or batch export training plans via the `/api/export/fit` endpoints
- **JSON:** Access your data via the API endpoints

### 4.2 Data Access
Access your data through:
- **Athlete context:** `/api/athlete/context` - Full athlete profile and metrics
- **Fitness metrics:** `/api/athlete/fitness-metrics` - Historical CTL/ATL/TSB
- **Workout history:** `/api/workouts` - All stored workouts
- **Race goals:** `/api/goals` - Your configured goals

### 4.3 Data Deletion
- **Race goals:** Can be deleted via API (`DELETE /api/goals/{id}`)
- **Workout analyses:** Can be deleted via the database
- **Full account deletion:** Contact the application administrator or manually delete the SQLite database files

### 4.4 Data Portability
The SQLite database format is open and portable. You can:
- Copy your `training.db` file to another system
- Use standard SQLite tools to query and export data
- Export workouts as FIT files for import into other platforms

---

## 5. Security Measures

### 5.1 Encryption
- **Credentials at rest:** Garmin credentials encrypted with Fernet (AES-128-CBC)
- **Data in transit:** All API calls use HTTPS
- **Session tokens:** JWT-based authentication with configurable expiration

### 5.2 Authentication
- JWT tokens with 30-minute access token expiration
- 7-day refresh token expiration
- Password hashing using bcrypt with salt

### 5.3 API Security
- Rate limiting implemented via slowapi
- SQL injection prevention through parameterized queries
- CORS configuration for cross-origin request control
- OAuth state parameter validation for third-party integrations

### 5.4 Recommendations for Users
- Use strong, unique passwords for your Garmin/Strava accounts
- Secure the `.env` file with appropriate file permissions (`chmod 600`)
- Secure database files with restricted permissions (`chmod 600 *.db`)
- Regularly review and revoke unused third-party integrations

---

## 6. Data Retention

### 6.1 Current Behavior
- Activity and fitness data is retained indefinitely unless manually deleted
- Workout analyses are cached and retained indefinitely
- AI usage logs are stored for cost tracking and analytics

### 6.2 Planned Improvements
- Configurable data retention periods
- Automatic cleanup of expired sessions
- Historical data archival options

---

## 7. Consent and Control

### 7.1 AI Analysis Consent
- AI-powered analysis features require an active OpenAI API key
- You control whether AI analysis is enabled via configuration
- Consider the data sharing implications before enabling AI features

### 7.2 Third-Party Integration Consent
- Garmin Connect integration requires providing your credentials
- Strava integration uses OAuth (you authorize specific permissions)
- You can revoke integrations at any time

---

## 8. Children's Privacy

This application is not intended for use by individuals under the age of 13. We do not knowingly collect personal information from children.

---

## 9. Changes to This Policy

We may update this privacy policy from time to time. Changes will be reflected in the "Last Updated" date at the top of this document.

---

## 10. Contact

For privacy-related questions or to exercise your data rights, contact the project maintainer.

---

## 11. Technical Reference

### Files Involved in Data Collection
- `training-analyzer/src/llm/context_builder.py` - Builds athlete context for LLM
- `training-analyzer/src/db/database.py` - Database schema and operations
- `training-analyzer/src/services/encryption.py` - Credential encryption

### Database Tables Containing Personal Data
- `user_profile` - Personal metrics and physiological data
- `activity_metrics` - Workout data with heart rate and performance metrics
- `fitness_metrics` - Daily CTL/ATL/TSB calculations
- `garmin_fitness_data` - VO2max, race predictions, training status
- `race_goals` - User-defined goals
- `garmin_credentials` - Encrypted Garmin login credentials
- `strava_tokens` - Strava OAuth tokens
- `user_sessions` - Session data including IP addresses (see Section 12 for GDPR considerations)

---

## 12. IP Address Storage and GDPR Compliance

### 12.1 What IP Addresses Are Collected

The application stores IP addresses in the `user_sessions` table for:
- **Security purposes:** Detecting suspicious login patterns and potential account compromise
- **Session management:** Tracking active sessions and their origins
- **Abuse prevention:** Rate limiting and blocking malicious actors

### 12.2 GDPR Considerations

Under the General Data Protection Regulation (GDPR), IP addresses are considered **personal data** because they can be used to identify individuals, particularly when combined with other information.

**Legal Basis for Processing:**
- **Legitimate interest (Article 6(1)(f)):** Storing IP addresses serves the legitimate interest of securing user accounts and preventing unauthorized access
- **Contract performance (Article 6(1)(b)):** Session tracking is necessary to provide the authentication service

### 12.3 Data Minimization and Retention

To comply with GDPR data minimization principles:

1. **Limited retention:** IP addresses are automatically deleted when sessions expire or are cleaned up (default: 30 days, configurable via `RETENTION_SESSIONS_DAYS`)
2. **Purpose limitation:** IP addresses are only used for security and session management, not for analytics or marketing
3. **Access control:** IP address data is only accessible to system administrators for security investigations

### 12.4 Disabling IP Address Logging

For maximum privacy or strict GDPR compliance, IP address logging can be disabled entirely:

```bash
# Add to .env file:
PRIVACY_LOG_IP_ADDRESSES=false
```

When disabled:
- New sessions will not record IP addresses
- Existing IP address data remains until sessions expire and are cleaned up
- Security features that rely on IP addresses (e.g., geo-anomaly detection) will be unavailable

### 12.5 Data Subject Rights

Users have the following rights regarding their IP address data:

- **Right of access (Article 15):** Request a copy of stored IP addresses via data export
- **Right to erasure (Article 17):** Request deletion of IP address data by deleting sessions
- **Right to object (Article 21):** Object to IP address processing; address by disabling IP logging

### 12.6 Security Measures for IP Data

IP addresses are protected by:
- Database file permissions (recommended: `chmod 600`)
- Automatic cleanup of expired sessions
- No transmission to third parties
- Not included in LLM/AI analysis data
