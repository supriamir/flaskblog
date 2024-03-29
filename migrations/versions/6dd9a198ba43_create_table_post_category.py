"""Create table post category

Revision ID: 6dd9a198ba43
Revises: 65b131b6a202
Create Date: 2022-01-02 00:29:28.756256

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6dd9a198ba43'
down_revision = '65b131b6a202'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('post_category',
    sa.Column('post', sa.Integer(), nullable=False),
    sa.Column('category', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['category'], ['category.id'], ),
    sa.ForeignKeyConstraint(['post'], ['post.id'], ),
    sa.PrimaryKeyConstraint('post', 'category')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('post_category')
    # ### end Alembic commands ###
