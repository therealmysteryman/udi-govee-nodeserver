git add profile.zip
git commit -m "Travis build: $TRAVIS_BUILD_NUMBER [skip ci]"
git branch tmp_$TRAVIS_BRANCH
git checkout $TRAVIS_BRANCH
git merge tmp_$TRAVIS_BRANCH
git remote add origin-pages https://$GITHUB_TOKEN@github.com/therealmysteryman/udi-twinkly-nodeserver
git push origin-pages $TRAVIS_BRANCH 
