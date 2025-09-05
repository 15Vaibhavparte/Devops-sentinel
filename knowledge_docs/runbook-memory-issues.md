# Runbook: Memory Issues Troubleshooting

## Topic: High Memory Usage and Out of Memory (OOM) Issues

**Keywords**: memory, high-memory, OOM, out-of-memory, memory-leak, RAM, heap, memory-usage, memory-optimization

### **Problem**: High Memory Usage or Out of Memory Errors

Applications consuming excessive memory, causing:
- System slowdowns
- OOMKilled pods in Kubernetes
- Application crashes
- Poor performance

### **Diagnosis Steps**

#### **1. Identify Memory Usage**
```bash
# Check system memory usage
free -h
top
htop

# For Kubernetes pods
kubectl top pods
kubectl top nodes

# Check specific pod memory
kubectl describe pod <pod-name>
kubectl logs <pod-name> | grep -i "memory\|oom"
```

#### **2. Check for Memory Leaks**
```bash
# Monitor memory over time
watch -n 5 'free -h'

# Check application-specific memory
# For Java applications
jstat -gc <pid>
jmap -heap <pid>

# For Node.js applications
node --inspect app.js
# Then use Chrome DevTools Memory tab
```

#### **3. Analyze OOM Events**
```bash
# Check system logs for OOM killer
dmesg | grep -i "killed process"
journalctl -u kubelet | grep -i "oom"

# Kubernetes events
kubectl get events --sort-by='.lastTimestamp' | grep -i "oom"
```

### **Resolution Steps**

#### **1. Immediate Actions**
- **Restart affected services** to free memory temporarily
- **Scale horizontally** if possible to distribute load
- **Increase memory limits** in Kubernetes if legitimate need exists

#### **2. Resource Optimization**
```yaml
# Kubernetes resource limits adjustment
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: app
        resources:
          requests:
            memory: "256Mi"
          limits:
            memory: "512Mi"  # Increase if needed
```

#### **3. Application-Level Fixes**
- **Code optimization**: Review memory-intensive operations
- **Garbage collection tuning**: Adjust GC settings for Java/Node.js
- **Connection pooling**: Optimize database connection pools
- **Caching strategies**: Implement efficient caching with TTL

#### **4. Monitoring and Prevention**
```bash
# Set up memory monitoring
kubectl apply -f memory-monitoring.yaml

# Create memory alerts in Grafana
# Alert when memory usage > 80%
# Alert when OOMKilled events occur
```

### **Common Causes**
- Memory leaks in application code
- Inefficient database queries loading large datasets
- Misconfigured JVM heap sizes
- Lack of proper resource limits in containers
- Inefficient caching implementations

### **Prevention**
- Regular memory profiling
- Proper resource limits and requests
- Memory usage monitoring and alerting
- Code reviews focusing on memory efficiency
- Load testing with memory constraints