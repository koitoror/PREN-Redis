var express = require('express');
var router = express.Router();

/* GET users listing. */
router.get('/', function(req, res, next) {
  res.send('respond with a resource');
});

app.get("/users/:userid/create", function (req, res, next) {
  // serve the form
});

app.post("/users/:userid/create", function (req, res, next) {
  // save in the database
});

module.exports = router;
