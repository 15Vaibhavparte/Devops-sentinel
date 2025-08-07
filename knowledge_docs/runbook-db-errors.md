# Runbook: Database Connection Errors

## Problem Description
The service fails to start or experiences intermittent failures, and logs show errors like "Connection refused," "Authentication failed," or "Database connection timeout." This indicates the application cannot communicate with the primary database.

## Root Causes
1.  **Incorrect Credentials:** The username or password in the environment variables (DB_USER, DB_PASSWORD) might be wrong or outdated.
2.  **Network Issues:** A firewall rule or network security group is blocking the connection from the application server to the database on port 3306.
3.  **Database Overload:** The database server itself might be down or overwhelmed with too many connections, refusing new ones.

## Resolution Steps
1.  **Verify Credentials:** Double-check the environment variables against the official credential store.
2.  **Check Network Connectivity:** Use a tool like `telnet` or `nc` from the application server to check if the database port is open. Example: `telnet db.example.com 3306`.
3.  **Inspect Database Health:** Check the database's monitoring dashboard for high CPU usage or an excessive number of active connections. If overloaded, consider scaling up the database instance.
# Database Error Runbook

## Common Database Issues

### Connection Timeouts
- Check network connectivity
- Verify database service is running
- Review connection pool settings

### Lock Timeouts
- Identify long-running queries
- Check for deadlocks
- Consider query optimization

### High CPU Usage
- Monitor slow queries
- Check index usage
- Review query execution plans

### Memory Issues
- Monitor buffer pool usage
- Check for memory leaks
- Review configuration settings