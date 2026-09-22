from sqlalchemy import CheckConstraint, String, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4

from app.db.models.too.z_base import Base, BaseMixin
from app.db.models.db_schemas import SCHEMA_TOO_ACC


class COADB(BaseMixin, Base):
    __tablename__ = "coa"
    __table_args__ = (
        UniqueConstraint("ten_id", "coa_code", name="uq_coa_ten_code"),
        {"schema": SCHEMA_TOO_ACC}
    )

    # 自引用外键
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_TOO_ACC}.coa.id", ondelete="RESTRICT"),
        nullable=True,        index=True    )
    
    # 业务字段
    coa_code: Mapped[str] = mapped_column(String(20), nullable=True)
    coa_name: Mapped[str] = mapped_column(String(255), nullable=True)  # 你原来没有，建议加上
    coa_status: Mapped[str] = mapped_column(String(20), nullable=True, default="Active")  # Active / Inactive
    
    # 层级（冗余字段，方便查询）
    coa_level: Mapped[int] = mapped_column(nullable=True)  # 1,2,3,4
    coa_template: Mapped[str] = mapped_column(String(20), nullable=True)  # 你原来没有，建议加上
   
    # 科目属性
    normal_balance: Mapped[str] = mapped_column(String(20), nullable=True)  # debit / credit
    is_posting: Mapped[bool] = mapped_column(default=True)  # True=可过账, False=汇总科目
    is_readonly: Mapped[bool] = mapped_column(default=False)
    
    # 关系（可选，方便ORM查询）
    parent: Mapped["COADB"] = relationship("COADB", remote_side="COADB.id", back_populates="children")
    children: Mapped[list["COADB"]] = relationship("COADB", back_populates="parent")



