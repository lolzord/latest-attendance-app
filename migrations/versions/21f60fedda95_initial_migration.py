"""Initial migration

Revision ID: 21f60fedda95
Revises: 
Create Date: 2024-05-15 12:44:20.351044

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '21f60fedda95'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Drop the unique constraint
    op.drop_constraint('UQ__user__AB6E6164473756E1', 'user', type_='unique')
    
    # Alter column
    op.alter_column('user', 'email', existing_type=sa.VARCHAR(length=150), type_=sa.String(length=120), nullable=False)
    op.alter_column('user', 'password', existing_type=sa.VARCHAR(length=150), type_=sa.String(length=200), nullable=False)
    
    # Recreate the unique constraint
    op.create_unique_constraint('uq_user_email', 'user', ['email'])

def downgrade():
    # Drop the new unique constraint
    op.drop_constraint('uq_user_email', 'user', type_='unique')
    
    # Revert column changes
    op.alter_column('user', 'email', existing_type=sa.String(length=120), type_=sa.VARCHAR(length=150), nullable=False)
    op.alter_column('user', 'password', existing_type=sa.String(length=200), type_=sa.VARCHAR(length=150), nullable=False)
    
    # Recreate the original unique constraint
    op.create_unique_constraint('UQ__user__AB6E6164473756E1', 'user', ['email'])
