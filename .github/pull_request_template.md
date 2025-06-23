Please ensure you've followed the checklist and provide all the required information *before* requesting a review.
If you do not have everything applicable to your PR, it will not be reviewed!
If you don't know what something is or if it applies to you, ask!

Please note that PRs from external contributors who have not agreed to [our Contributor License Agreement](/CLA.md) will not be considered.
To accept it, include `I agree to the [current Contributor License Agreement](/CLA.md)` in this pull request.

Don't delete below this line.

---

## Required Information

- [ ] I referenced the issue addressed in this PR.
- [ ] I described the changes made and how these address the issue.
- [ ] I described how I tested these changes.

## Coding/Commit Requirements

* [ ] I followed applicable coding standards where appropriate (e.g., [PEP8](https://pep8.org/))
* [ ] I have not committed any models or other large files.

## New Component Checklist (**mandatory** for new microservices)

* [ ] I added an entry to `docker-compose.yml` and `build.yml`.
* [ ] I created A CI workflow under `.github/workflows`.
* [ ] I have created a `README.md` file that describes what the component does and what it depends on (other microservices, ML models, etc.).

OR
* [ ] I have not added a new component in this PR.
