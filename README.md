This repository holds the code for the Charm SDK tutorial for Kubernetes: https://juju.is/docs/sdk/from-zero-to-hero-write-your-first-kubernetes-charm 

There is a branch for each chapter. As the chapters build on top of one other, each branch builds on the one before as well. As a result:

- To create a branch for a new chapter: Create it from the latest branch.

- To make make a change to a chapter and then propagate it up to all the remaining branches:
    -  Start with the first branch (Branch A) and make the necessary updates. Commit the changes in Branch A.
    -  Switch to the second branch (Branch B). Merge the changes from Branch A into Branch B. Resolve any conflicts that arise during the merge process, if applicable. Commit the changes resulting from the merge in Branch B.
    -  Repeat for each branch until you're done. Your changes should have successfully propagated to all the branches.

⚠️ In either case, once you've made the change in the repository, make sure to update the code in the corresponding tutorial chapter as well. (From the juju.is link, on the bottom of each doc, click on "Help improve this document in the forum", then edit the doc on Discourse. Make sure to also add your name to the list of contributors on the bottom of each doc.)
