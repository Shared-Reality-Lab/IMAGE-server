FROM schemas:latest AS schemas
FROM continuumio/miniconda3

COPY --from=schemas /schemas /app/schemas

WORKDIR /chart-pipeline

RUN apt-get update && apt-get install unzip

COPY environment.yml environment.yml
RUN conda env create -f environment.yml
RUN echo "source activate chartenv" > ~/.bashrc

ENV PATH /opt/conda/envs/chartenv/bin:$PATH

COPY . .

RUN pip install gdown
RUN gdown https://drive.google.com/uc?id=1qtCLlzKm8mx7kQOV1criUbqcGnNh58Rr
RUN unzip ./Chart-pipeline-models.zip
RUN rm ./Chart-pipeline-models.zip
RUN mv ./data/clsdata\(1031\)/cls ./data/clsdata\(1031\)/Cls

ENTRYPOINT ["python3", "-m" , "app"]
