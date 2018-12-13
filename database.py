#!/usr/bin/python
# -*- coding: utf-8 -*-

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

# We define tables and catalogs relatively, by building upon this base

Base = declarative_base()


# Calling String with an argument, limits the number of
# characters the string can contain # ForeignKey constrains
# a Column to only accept values present in another Column
# @propery creates a propert of a class
# serialize produces a json stringable object for a row

class User(Base):

    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    google_id = Column(String,  nullable=False, unique=True)
    picture = Column(String,  nullable=False)

    @property
    def serialize(self):
        return {'id': self.id, 'name': self.name,
                'picture': self.picture}


class Category(Base):

    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship(User)

    @property
    def serialize(self):
        return {'id': self.id, 'name': self.name,
                'user_id': self.user_id}


class Item(Base):

    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey('category.id'),
                         nullable=False)
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category_id': self.category_id,
            'user_id': self.user_id,
            }


engine = create_engine('sqlite:///itemize.db')

# Creates all of our Tables using the created engine

Base.metadata.create_all(engine)
