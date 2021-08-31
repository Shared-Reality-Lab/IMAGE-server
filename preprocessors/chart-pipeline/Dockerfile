FROM schemas:latest AS schemas
FROM continuumio/miniconda3

COPY --from=schemas /schemas /app/schemas

WORKDIR /chart-pipeline

COPY environment.yml environment.yml
RUN conda env create -f environment.yml
RUN echo "source activate chartocr" > ~/.bashrc

ENV PATH /opt/conda/envs/chartocr/bin:$PATH

COPY . .

RUN pip install gdown
RUN gdown https://drive.google.com/uc?id=1qtCLlzKm8mx7kQOV1criUbqcGnNh58Rr
RUN unzip Chart-pipieline-models.zip
RUN mv Chart-pipeline-models/data /chart-pipeline/
RUN rm -r Chart-pipeline-models
RUN mv /chart-pipeline/data/clsdata\(1031\)/cls /chart-pipeline/data/clsdata\(1031\)/Cls

ENTRYPOINT ["python3", "-m" , "app"]
