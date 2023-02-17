Docker Setup

docker build --tag container-agent .
docker run --network=host container-agent