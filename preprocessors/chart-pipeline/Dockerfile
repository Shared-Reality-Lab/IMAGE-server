FROM schemas:latest AS schemas
FROM continuumio/miniconda3

COPY --from=schemas /schemas /chart-pipeline/schemas

WORKDIR /chart-pipeline

RUN apt-get update && apt-get install unzip && apt-get install -y g++
RUN pip install gdown

COPY environment.yml environment.yml
RUN conda env create -f environment.yml
RUN echo "source activate chartenv" > ~/.bashrc

ENV PATH /opt/conda/envs/chartenv/bin:$PATH

COPY . .

WORKDIR /chart-pipeline/models/kp_models/_cpool_layers
ENV CXX g++
RUN python setup.py build_ext --inplace && rm -r build

WORKDIR /chart-pipeline

RUN pip install gunicorn
RUN gdown https://drive.google.com/uc?id=1qtCLlzKm8mx7kQOV1criUbqcGnNh58Rr
RUN unzip Chart-pipeline-models.zip
RUN rm Chart-pipeline-models.zip
RUN mv data/clsdata\(1031\)/cls data/clsdata\(1031\)/Cls

RUN gdown https://drive.google.com/uc?id=1-4PDJ9JHAOGtyLkvVHAHVuo0xGERC1XL
RUN unzip pycocotool.zip
RUN rm pycocotool.zip

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]
