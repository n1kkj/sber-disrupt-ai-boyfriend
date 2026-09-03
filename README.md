### **Basic fastapi + alembic (async postgres) template**

__V 1.0__

----

This is free to use fastapi template from @n1kkj

I personally used it in many of my projects, including fully working sites, services in big micro-service structures, telegram bots and more!

It uses uvicorn and docker to run, the command for start and restart:

```
docker compose up -d --build --force-recreate
```

And to stop containers:
```
docker compose down
```

To generate and perform alembic migrations:

```
alembic revision --autogenerate -m "init"
alembic upgrade head
```

Contact me in telegram @n1kkj if you have any suggestions or questions

**Or**

Comment on [discussion page](https://github.com/n1kkj/fastapi-template/discussions/1)

----

## Lets create best fastapi apps together!
