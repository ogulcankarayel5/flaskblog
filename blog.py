from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,validators,PasswordField
from passlib.hash import sha256_crypt
from passlib.apps import custom_app_context as pwd_context
from functools import wraps

class RegisterForm(Form):
    name=StringField("İsim ve Soyisim",validators=[validators.Length(min=5,max=35,message="Lütfen en az 5 uzunlukta olacak şekilde isim ve soyisminizi girin")])
    username=StringField("Kullanıcı Adı",validators=[validators.Length(min=5,max=35,message="Kullanıcı Adınız en az 5 karakterli olmalı")])
    email=StringField("Email",validators=[validators.Email(message="Lütfen geçerli bir email giriniz")])
    password=PasswordField("Şifre",validators=[
        
        validators.DataRequired("Şifre Boş Bırakılamaz"),
        validators.EqualTo(fieldname="confirm",message="Şifre onaylama başarısız"),
        validators.Length(min=6,max=30,message="Şifre uzunluğunuz en az 6 karakter olmalı")
    
    ])
    confirm=PasswordField("Şifre Doğrula",validators=[validators.Length(min=6,max=30)])
#Giris Formu
class LoginForm(Form):
    username=StringField("Giriş Yap")
    password=PasswordField("Şifre Gir")

#Makale formu
class ArticleForm(Form):
    title=StringField("Makale Başlığı",validators=[validators.Length(min=5,max=100)])
    content=TextAreaField("Makale İçeriği",validators=[validators.Length(min=10)])



#Kullanıcı giriş kontrol decoratar'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu bölüme girmek için,Giriş yapmanız gerekmekte","danger")
            return redirect(url_for("login"))
        
    return decorated_function


app=Flask(__name__)
app.secret_key="ybblog"

app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="ybblog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"
mysql=MySQL(app)


@app.route("/")
def index():

   return render_template("index.html")
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/register",methods=["GET","POST"])
def register():
    form=RegisterForm(request.form)

    if request.method=="POST" and form.validate():
        cursor=mysql.connection.cursor()

        name=form.name.data
        username=form.username.data
        email=form.email.data
        password=sha256_crypt.encrypt(form.password.data)

        insertSorgu="insert into users (name,email,username,password) values (%s,%s,%s,%s)"
        cursor.execute(insertSorgu,(name,username,email,password))
        mysql.connection.commit()

        cursor.close()
        flash("Başarıyla Kayıt Oldunuz","success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)

@app.route("/login",methods=["GET","POST"])
def login():
    form=LoginForm(request.form)
    if request.method=="POST":
        username=form.username.data
        password=form.password.data

        cursor=mysql.connection.cursor()
        sorgu="select * from users where username=%s"
        result=cursor.execute(sorgu,(username,))

        if result>0:
            data=cursor.fetchone()
            realPassword=data["password"]
            if pwd_context.verify(password,realPassword):
                flash("Başarıyla Giriş Yaptınız","success")

                session["logged_in"]=True
                session["username"]=username

                return redirect(url_for("index"))
            else:
                flash("Parolanız Yanlış","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı yok","danger")
            return redirect(url_for("login"))
    else:
        return render_template("login.html",form=form)
    
#logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla Çıkış Yapıldı","success")
    return redirect(url_for("index"))

@app.route("/article/<string:id>")
def article(id):
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where id=%s"
    result=cursor.execute(sorgu,(id,))
    if result>0:
        article=cursor.fetchone()
        return render_template("/article.html",article=article)
    else:
        return render_template("/article.html")
    

@app.route("/dashboard")
@login_required
def dashboard():
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where author=%s"
    result=cursor.execute(sorgu,(session["username"],))
    if result>0:
        articles=cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")
#Makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where author=%s and id=%s"
    result=cursor.execute(sorgu,(session["username"],id))
    
    if result>0:
        sorgu2="delete from articles where id=%s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()

        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya silmeye yetkiniz yok","danger")
        return redirect(url_for("index"))

#Makale Guncelleme
@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def update(id):
    if request.method=="GET":
        cursor=mysql.connection.cursor()
        sorgu="select * from articles where id=%s and author=%s"
        result=cursor.execute(sorgu,(id,session["username"]))

        if result>0:
            article=cursor.fetchone()
            form=ArticleForm()

            form.title.data=article["title"]
            form.content.data=article["content"]

            return render_template("update.html",form=form)


        else:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
            return redirect(url_for("index"))
        
    else:
        form=ArticleForm(request.form)

        newTitle=form.title.data
        newContent=form.content.data
        cursor=mysql.connection.cursor()
        sorgu="update articles set title=%s,content=%s where id=%s"
        cursor.execute(sorgu,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Makale güncelleme işlemi başarılı","success")
        return redirect(url_for("dashboard"))



@app.route("/addarticles",methods=["GET","POST"])
def addarticles():
    form=ArticleForm(request.form)
    if request.method=="POST" and form.validate():
        title=form.title.data
        author=session["username"]
        content=form.content.data

        cursor=mysql.connection.cursor()

        sorgu="insert into articles (title,author,content) values (%s,%s,%s)"
        cursor.execute(sorgu,(title,author,content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarıyla oluşturuldu","success")
        return redirect(url_for("dashboard"))
        
    else:

        return render_template("addarticles.html",form=form)  
@app.route("/articles")
def articles():
    cursor=mysql.connection.cursor()
    sorgu="select * from articles"
    result=cursor.execute(sorgu)
    
    if result>0:
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")

 #Makale Arama
 
@app.route("/search",methods=["GET","POST"])
def search():
    if request.method=="GET":
         
        return redirect(url_for("articles"))
    else:
        keyword=request.form.get("keyword")
        cursor=mysql.connection.cursor()
        sorgu="select * from articles where title like '%" + keyword +"%' "
        result=cursor.execute(sorgu)
        
        if result>0:
            articles=cursor.fetchall()
            return render_template("articles.html",articles=articles)
        else:
            flash("Aradığınız kelimeye uygun makale bulunamadı.Üzgünüz")
            return redirect(url_for("index"))
            
if __name__=="__main__":
    app.run(debug=True)