# Mini-Sprint 2025–01

## `findingmodelforge`

- [ ] Update the `finding_model` definition:
  - [ ] Add `author`, pointing to the `user` table
  - [ ] Add finding model and attribute identifiers
  - [ ] Auto-assign finding model and attribute identifiers
  - [ ] Add links to eventual CDE codes (temp, permanent)
  - [ ] Include ability to have links to ontologies
  - [ ] Include batch creation of 
- [ ] Add a `user` object so we can keep track of who we have
  - [ ] Pick the right GitHub attributes to cache
  - [ ] Add local info, especially some kind of authorization (`admin` flag?)
- [ ] Represent CDEs from [RadElement](https://radelement.org) in the LanceDB to enable searching

## `fmf_cli`

- [ ] Make the stub-creation method do a search for an existing model (including those from CDEs) before creating
- [ ] Add a method to take in a whole list of finding model names and produce stubs

## `fmf-api` → `fmf_web`

- [ ] Rename to `fmf_web`
- [ ] Take logins and save the Github data to our `user` table
- [ ] Make our stub creation tool actually save items to the database
- [ ] Make our stub creation look for existing models before creation
- [ ] Add a index of existing FMs (big table)
  - [ ] Filter the index by tags, etc.
- [ ] Add a search function to look for finding models
- [ ] Clean up the main page layout

