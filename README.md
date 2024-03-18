This repository holds the code for the Charm SDK tutorial for Kubernetes: https://juju.is/docs/sdk/from-zero-to-hero-write-your-first-kubernetes-charm 

There is a branch for each chapter. 

As the chapters build on top of each other, each branch builds on the one before as well. 

As a result, if you make a change to one chapter, propagate it up to all the remaining branches, following this pattern:

1. Start with the first branch (Branch A) and make the necessary updates. Commit the changes in Branch A.

2. Switch to the second branch (Branch B). Merge the changes from Branch A into Branch B. Resolve any conflicts that arise during the merge process, if applicable. Commit the changes resulting from the merge in Branch B.

3-n. Repeat for each branch until you're done.

Your changes should have successfully propagated to all the branches.
