from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Table
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Writer(Base):
    __tablename__ = 'writer'
    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False, unique=False)
    posts = relationship("Post")
    comments = relationship("Comment")


post_tag_table = Table('post_tag', Base.metadata,
                       Column('post_id', String, ForeignKey('post.id')),
                       Column('tag_id', String, ForeignKey('tag.id'))
                       )


class Post(Base):
    __tablename__ = 'post'
    id = Column(String, primary_key=True)
    url = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False, unique=False)
    posted_at = Column(DateTime, nullable=True, unique=False)
    img_src = Column(String, nullable=True, unique=False)
    writer_id = Column(Integer, ForeignKey('writer.id'))
    writer = relationship("Writer")
    tags = relationship("Tag", secondary=post_tag_table)
    comments = relationship("Comment")


class Tag(Base):
    __tablename__ = 'tag'
    id = Column(String, primary_key=True)
    posts = relationship("Post", secondary=post_tag_table)


class Comment(Base):
    __tablename__ = 'comment'
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('comment.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, unique=False)
    body = Column(String, nullable=True, unique=False)
    post_id = Column(String, ForeignKey('post.id'))
    post = relationship("Post")
    writer_id = Column(Integer, ForeignKey('writer.id'))
    writer = relationship("Writer")
