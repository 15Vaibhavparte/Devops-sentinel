# Runbook: Application Server Errors

## Topic: HTTP 502 Bad Gateway
- **Problem:** A user or service receives a 502 error, indicating that an upstream server (like your application) sent an invalid response to a gateway or proxy (like NGINX or a load balancer).
- **Diagnosis & Resolution:**
  1. **Check Application Logs:** Investigate the application logs at the time of the error. Look for application crashes, startup failures, or fatal errors that would cause the process to stop running.
  2. **Health Checks:** Review your load balancer's health check configuration. If the health checks are failing, the load balancer will correctly mark the instance as unhealthy and stop sending traffic to it, which can result in 502s if no other healthy instances are available.
  3. **Resource Exhaustion:** Check for memory or CPU exhaustion on the application server. If the application has crashed due to an Out-of-Memory (OOM) error, you will need to increase server resources or optimize the application's memory usage.

## Topic: HTTP 504 Gateway Timeout
- **Problem:** A gateway or proxy did not receive a timely response from an upstream server. This means your application is running but is taking too long to process a request.
- **Diagnosis & Resolution:**
  1. **Long-Running Processes:** Identify if the application is performing a long-running task, such as a complex database query, a call to a slow third-party API, or a heavy computation.
  2. **Database Performance:** A 504 error is often a symptom of a slow database query. Use the database runbook to diagnose any potential database performance issues that could be impacting your application's response time.
  3. **Increase Gateway Timeout:** As a temporary measure, you can increase the timeout value on the gateway or load balancer. However, the primary focus should be on optimizing the underlying application performance.