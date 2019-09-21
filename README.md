npx express-generator

express --view=pug myapp                                              at ⎈ docker-desktop

   create : myapp/
   create : myapp/public/
   create : myapp/public/javascripts/
   create : myapp/public/images/
   create : myapp/public/stylesheets/
   create : myapp/public/stylesheets/style.css
   create : myapp/routes/
   create : myapp/routes/index.js
   create : myapp/routes/users.js
   create : myapp/views/
   create : myapp/views/error.pug
   create : myapp/views/index.pug
   create : myapp/views/layout.pug
   create : myapp/app.js
   create : myapp/package.json
   create : myapp/bin/
   create : myapp/bin/www

change directory:
    $ cd myapp

install dependencies:
    $ npm i

run the app:
    $ DEBUG=myapp:* npm start