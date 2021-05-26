import express from "express";

const app = express();
const port = 80;

app.use(express.json());

app.post("/atp/handler", (req, res) => {
    console.debug(req.body);
    res.status(200);
});

app.listen(port, () => {
    console.log(`Started server on port ${port}`);
});
