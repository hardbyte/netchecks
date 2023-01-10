---
title: Getting started
pageTitle: Netchecks - Verifying your security controls
description: A cloud native tool to dynamically declare a set of statements about the network (what should work and what shouldn't)
---

Learn how to get Netchecks set up in your own Kubernetes cluster. {% .lead %}

{% quick-links %}

{% quick-link title="Installation" icon="installation" href="/" description="Step-by-step guides to setting up your system and installing the library." /%}

{% quick-link title="Architecture guide" icon="presets" href="/" description="Learn how the internals work and contribute." /%}

{% quick-link title="API reference" icon="theming" href="/" description="Learn to easily customize and modify your app's visual design to fit your brand." /%}

{% quick-link title="Examples" icon="plugins" href="/" description="See how others are using the library in their projects." /%}

{% /quick-links %}

Possimus saepe veritatis sint nobis et quam eos. Architecto consequatur odit perferendis fuga eveniet possimus rerum cumque. Ea deleniti voluptatum deserunt voluptatibus ut non iste.

---
## Quick start

### Installation

Install the `NetworkAssertion` and `PolicyReport` CRDs and the `Netchecks` operator with:

```bash
kubectl apply -f https://github.com/netchecks/operator/raw/main/manifests/crds/networkassertion-crd.yaml
kubectl apply -f https://github.com/kubernetes-sigs/wg-policy-prototypes/raw/master/policy-report/crd/v1alpha2/wgpolicyk8s.io_policyreports.yaml
kubectl create namespace netchecks
kubectl apply -f manifests/operator -n netchecks
```

Wait until the netchecks namespace is running a Deployment with a ready Pod:

```shell
kubectl wait Deployment -n netchecks -l app=netcheck-operator --for condition=Available --timeout=90s
```

### Basic Usage

Create and apply your `NetworkAssertions` as any other Kubernetes resource.

For example a `NetworkAssertion` that checks HTTP requests to the Kubernetes API should succeed:


```yaml
apiVersion: hardbyte.nz/v1
kind: NetworkAssertion
metadata:
  name: http-k8s-api-should-work
  namespace: default
  annotations:
    description: Assert pod can connect to k8s API
spec:
  template:
    metadata:
      labels:
        optional-label: applied-to-test-pod
  schedule: "@hourly"
  rules:
    - name: kubernetes-version
      type: http
      url: https://kubernetes/version
      verify-tls-cert: false
      expected: pass
      validate:
        message: Http request to Kubernetes API should succeed.
```



{% callout title="What happens next?" %}
Once you have applied the `NetworkAssertion`, netchecks reacts by creating a `CronJob` in the
same namespace to schedule the test. After the first test has run Netchecks creates a `PolicyReport` resource with the same name in the same namespace as the `NetworkAssertion`.
{% /callout %}

---

## Example Assertions

Praesentium laudantium magni. Consequatur reiciendis aliquid nihil iusto ut in et. Quisquam ut et aliquid occaecati. Culpa veniam aut et voluptates amet perspiciatis. Qui exercitationem in qui. Vel qui dignissimos sit quae distinctio.

### HTTP Assertions


Minima vel non iste debitis. Consequatur repudiandae et quod accusamus sit molestias consequatur aperiam. Et sequi ipsa eum voluptatibus ipsam. Et quisquam ut.

Qui quae esse aspernatur fugit possimus. Quam sed molestiae temporibus. Eum perferendis dignissimos provident ea et. Et repudiandae quasi accusamus consequatur dolore nobis. Quia reiciendis necessitatibus a blanditiis iste quia. Ut quis et amet praesentium sapiente.

Atque eos laudantium. Optio odit aspernatur consequuntur corporis soluta quidem sunt aut doloribus. Laudantium assumenda commodi.

### DNS Assertions

Vel aut velit sit dolor aut suscipit at veritatis voluptas. Laudantium tempore praesentium. Qui ut voluptatem.

Ea est autem fugiat velit esse a alias earum. Dolore non amet soluta eos libero est. Consequatur qui aliquam qui odit eligendi ut impedit illo dignissimos.

Ut dolore qui aut nam. Natus temporibus nisi voluptatum labore est ex error vel officia. Vero repellendus ut. Suscipit voluptate et placeat. Eius quo corporis ab et consequatur quisquam. Nihil officia facere dolorem occaecati alias deleniti deleniti in.



## Next Steps

### Policy Reporter Integration

#### UI
#### Alerts
#### Reports
#### Metrics

Officia nobis tempora maiores id iusto magni reprehenderit velit. Quae dolores inventore molestiae perspiciatis aut. Quis sequi officia quasi rem officiis officiis. Nesciunt ut cupiditate. Sunt aliquid explicabo enim ipsa eum recusandae. Vitae sunt eligendi et non beatae minima aut.

Harum perferendis aut qui quibusdam tempore laboriosam voluptatum qui sed. Amet error amet totam exercitationem aut corporis accusantium dolorum. Perspiciatis aut animi et. Sed unde error ut aut rerum.

Ut quo libero aperiam mollitia est repudiandae quaerat corrupti explicabo. Voluptas accusantium sed et doloribus voluptatem fugiat a mollitia. Numquam est magnam dolorem asperiores fugiat. Soluta et fuga amet alias temporibus quasi velit. Laudantium voluptatum perspiciatis doloribus quasi facere. Eveniet deleniti veniam et quia veritatis minus veniam perspiciatis.

