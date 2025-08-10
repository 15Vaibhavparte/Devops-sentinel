# Runbook: Kubernetes Container Issues

## Topic: CrashLoopBackOff
- **Problem:** A pod is starting, crashing, and then continuously being restarted by Kubernetes, but it never reaches a "Running" state.
- **Diagnosis & Resolution:**
  1. **Check Pod Logs:** The first step is always to check the logs of the crashing container. Use the command `kubectl logs <pod-name> -c <container-name>`. This will usually show the error that caused the application to exit.
  2. **Check Previous Pod Logs:** If the pod is crashing instantly, you may not see any logs. In this case, you need to get the logs from the *previous* terminated container. Use the command `kubectl logs <pod-name> -c <container-name> --previous`.
  3. **Describe the Pod:** Use `kubectl describe pod <pod-name>`. Look at the "Events" section at the bottom. This will often show why the pod is failing, such as "Failed to pull image," "OOMKilled" (Out of Memory), or failed liveness/readiness probes.
  4. **Configuration Issues:** A common cause is a misconfigured environment variable, a missing ConfigMap or Secret, or an incorrect command in the Dockerfile. Double-check all configuration files related to the deployment.