---
title: Writing plugins
description: How to write a plugin for Netchecks
---


{% callout type="warning" title="Not Implemented Yet" %}

The plugin architecture is still under design. Please get in touch if you'd like to help.

{% /callout %}

## Plugin goals

Netchecks will provide a plugin framework that allows:

- extending the set of network assertions with new types of checks. 


Currently, the Netcheck probe command line tool is written in Python. The plugin framework will allow writing 
assertions in other languages such as Rust, Go, or C. 

There are a couple of options for installing plugins in the Netcheck probe. The first is to install the 
plugin as a Python package in the main distributed container before running any assertions - although this
assumes the Python package (e.g. on PyPi) can be reached. The second is to install the plugin in a separate
Docker image.

Likely users will be able to build their own Docker images that build upon the Netcheck probe
base image adding plugins for custom assertions.

The operator needs to be know to use the appropriate Docker image - this could be done by:
- configuring the default probe image for all NetworkAssertions during operator installation, or 
- configuring the probe image for each NetworkAssertion individually.

