FROM schemas:latest AS schemas
FROM continuumio/miniconda3

COPY --from=schemas /schemas /chart-pipeline/schemas

WORKDIR /chart-pipeline

RUN apt-get update && apt-get install unzip && apt-get install -y g++


COPY environment.yml environment.yml
RUN conda env create -f environment.yml
RUN echo "source activate chartenv" > ~/.bashrc

ENV PATH /opt/conda/envs/chartenv/bin:$PATH

COPY . .

WORKDIR /chart-pipeline/models/kp_models/_cpool_layers
ENV CXX g++
RUN python setup.py build_ext --inplace && rm -r build

WORKDIR /chart-pipeline

RUN chmod +x boot.sh
RUN pip install gunicorn==20.1.0
RUN wget https://image.a11y.mcgill.ca/models/chart/Chart-pipeline-models.zip
RUN unzip Chart-pipeline-models.zip
RUN rm Chart-pipeline-models.zip
RUN mv data/clsdata\(1031\)/cls data/clsdata\(1031\)/Cls

RUN wget https://image.a11y.mcgill.ca/models/chart/pycocotool.zip
RUN unzip pycocotool.zip
RUN rm pycocotool.zip

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]
