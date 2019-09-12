# ----------------------------------------------------------------------------------------------------------------------
# Stage 0: Setup docker environment with vsh runtime dependencies
FROM python:3.7-alpine as base
ENV PREFIX_PATH /install
ENV APP_PATH /app
ENV HOME /root

WORKDIR $APP_PATH

# ----------------------------------------------------------------------------------------------------------------------
# Stage 1:  vsh build dependencies
# This section defines the first stage of a multistage build.
# This stage creates the base image containing everything except the vsh
# package itself.
FROM base as builder

# build is used to minimize the size of the docker image
#  by copying the built binaries into the app base image
RUN echo "---------- Creating builder ----------" \
 && apk --no-cache add --update --virtual build-dependencies \
    git \
    build-base \
    linux-headers \
    python3-dev \
 && mkdir $PREFIX_PATH \
# requirements are here because they require build-dependencies above
#  but build-dependencies are not required for operation, just for
#  installation.  So install the requirements here.
 && apk del build-dependencies \
 && rm -f /var/cache/apk/* \
 && echo "Builder created"

# ----------------------------------------------------------------------------------------------------------------------
# Stage 2:  Build vsh
# This section is the application installation and nothing else.
FROM base as app_base
COPY --from=builder $PREFIX_PATH /usr/local
COPY ./setup.py $APP_PATH/setup.py
COPY ./entrypoints.txt $APP_PATH/entrypoints.txt
COPY ./vsh $APP_PATH/vsh

RUN echo "---------- Creating app base ------------" \
 && apk --no-cache add --virtual runtime-dependencies \
    git \
 && python setup.py clean \
 && pip install --upgrade pip \
 && pip install $APP_PATH \
 && rm -f /var/cache/apk/* \
 && echo "---------- Finished app base ------------"

# ----------------------------------------------------------------------------------------------------------------------
# Stage 3: Test vsh
# Validate build
FROM app_base as test_base

COPY ./requirements $APP_PATH/requirements
COPY ./.coveragerc $APP_PATH/.coveragerc
COPY ./.flake8 $APP_PATH/.flake8
COPY ./mypy.ini $APP_PATH/mypy.ini
COPY ./pytest.ini $APP_PATH/pytest.ini
COPY ./tox.ini $APP_PATH/tox.ini
COPY ./scripts $APP_PATH/scripts
COPY ./tests $APP_PATH/tests

WORKDIR $APP_PATH

RUN echo "---------- Testing ------------" \
 && apk --no-cache add --virtual test-dependencies \
    build-base \
    curl \
    gcc \
 && gcc --version \
 && pip install --upgrade pip \
 && pip install -e $APP_PATH[test] \
 # We run the tests without type annotations or styles
 && pytest -n 4 -v -x -r a --cov \
 # then we check styles
 && flake8 \
 && isort -v -c --skip=vsh/vendored \
# # then we check type annotations
# && mypy vsh \
 && apk del test-dependencies \
 && rm -f /var/cache/apk/* \
 && echo "------ finished tests ---------"

# Use app_base for standard execution
FROM app_base

CMD ["vsh"]
