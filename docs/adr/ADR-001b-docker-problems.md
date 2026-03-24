# Why Dockerizing a Monolith Isn't Enough

## The Problem We Discovered

Even after containerizing the monolith, core problems remain:

1. **Image size**: The monolith image is large because it contains ALL dependencies
   for auth, products, orders, AND notifications. Each microservice image only
   needs its own dependencies — much smaller and faster to pull.

2. **Restart blast radius**: If the notification code crashes, Kubernetes restarts
   the ENTIRE monolith container, briefly taking down auth and products too.

3. **Scaling inefficiency**: We cannot tell Kubernetes "scale up only the product
   service" — it's all one container.

This is why containerizing alone isn't the solution. We need decomposition first.