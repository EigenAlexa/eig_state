To run the tests run 
``` docker run -e AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... -it --rm -v $(pwd):/app eig_brain nosetests --nologcapture ```
