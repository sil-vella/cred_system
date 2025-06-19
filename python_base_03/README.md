# Credit System API

## Configuration System

The application uses a layered configuration system:

1. **Environment Variables** (Highest Priority)
   - Loaded from `.env` file in development
   - Set in Kubernetes ConfigMaps/Secrets in production
   - Override all other configuration sources

2. **Vault Integration**
   - Database credentials are stored in Vault
   - Accessed through Kubernetes authentication
   - Mounted at `/vault/secrets/`

3. **Default Configuration** (`config.py`)
   - Contains sensible defaults for all settings
   - Used when environment variables are not set
   - Organized by feature/component

### Development Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update values in `.env` as needed
   - Most defaults are suitable for local development
   - Update sensitive values (passwords, keys, etc.)
   - Keep `.env` out of version control

### Production Setup

In production, configuration is managed through:
- Kubernetes ConfigMaps for non-sensitive data
- Kubernetes Secrets for sensitive data
- Vault for database credentials
- Environment variables in deployment manifests

### Configuration Categories

1. **Application Settings**
   - Flask configuration
   - Application URLs
   - Debug settings

2. **Security Settings**
   - JWT configuration
   - Rate limiting
   - Auto-ban settings

3. **Database Settings**
   - MongoDB connection
   - Redis configuration
   - Connection pooling

4. **Business Logic**
   - Credit limits
   - Transaction rules
   - Validation settings 