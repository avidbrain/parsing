from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

import orm


class DBStage:

    def __init__(self, db_url: str):
        engine = create_engine(db_url)
        orm.Base.metadata.create_all(bind=engine)
        self.session_m = sessionmaker(bind=engine)

    def close(self):
        pass

    def save(self, data):
        session = self.session_m()
        tags = []
        if 'tags' in data:
            for tag_id in data.pop('tags'):
                tag = orm.Tag(id=tag_id)
                session.merge(tag)
                tags.append(tag)
        comments = []
        if 'comments' in data:
            for comment_data in data.pop('comments'):
                comment_writer = orm.Writer(**comment_data.pop('writer'))
                session.merge(comment_writer)
                comment = orm.Comment(**comment_data)
                comment.writer = comment_writer
                session.merge(comment)
                comments.append(comment)
        writer = orm.Writer(**data.pop('writer'))
        session.merge(writer)
        post = orm.Post(**data)
        post.writer = writer
        post.tags = tags
        post.comments = comments
        session.merge(post)

        try:
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
        finally:
            session.close()
