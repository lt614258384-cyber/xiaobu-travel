"""管理命令入口。用法: python manage.py <command> [options]"""
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))


def cmd_init_owner():
    import argparse
    from models import init_db, get_session, User, Profile, JourneyState, JourneyLog, ScheduledTask
    from crypto_utils import hash_password

    parser = argparse.ArgumentParser(description="创建管理员账号并认领旧数据")
    parser.add_argument("--email", required=True, help="管理员邮箱")
    parser.add_argument("--password", required=True, help="管理员密码（至少 8 位）")
    parser.add_argument("--pet-name", default="小布", help="宠物名")
    args = parser.parse_args(sys.argv[2:])  # skip 'manage.py init-owner'

    if len(args.password) < 8:
        print("错误：密码至少 8 位")
        sys.exit(1)

    init_db()
    sess = get_session()
    try:
        # Check if any user already exists
        existing = sess.query(User).first()
        if existing:
            print("错误：数据库中已有用户。请通过网页注册新用户。")
            sys.exit(1)

        user = User(
            email=args.email,
            password_hash=hash_password(args.password),
            pet_name=args.pet_name,
            is_admin=True,
        )
        sess.add(user)
        sess.commit()
        sess.refresh(user)

        # Migrate old data
        updated = 0
        for model in [Profile, JourneyState, JourneyLog, ScheduledTask]:
            count = sess.query(model).filter(model.user_id == None).update(
                {model.user_id: user.id}, synchronize_session=False
            )
            updated += count

        sess.commit()
        print(f"创建管理员 {args.email}，迁移了 {updated} 条旧记录")

        # Migrate image files
        _migrate_user_files(user.id, args.pet_name)

    except Exception as e:
        sess.rollback()
        print(f"错误：{e}")
        sys.exit(1)
    finally:
        sess.close()


def _migrate_user_files(user_id: int, pet_name: str):
    """Move old uploads/generated/features to user-scoped directories."""
    import shutil

    data_dir = Path("data")

    # Move uploads
    old_uploads = data_dir / "uploads"
    new_uploads = data_dir / "uploads" / str(user_id)
    new_uploads.mkdir(parents=True, exist_ok=True)
    for f in old_uploads.iterdir():
        if f.is_file():
            shutil.move(str(f), str(new_uploads / f.name))
    print(f"已迁移上传照片到 {new_uploads}")

    # Move generated
    old_gen = data_dir / "generated"
    new_gen = data_dir / "generated" / str(user_id)
    new_gen.mkdir(parents=True, exist_ok=True)
    for f in old_gen.iterdir():
        if f.is_file():
            shutil.move(str(f), str(new_gen / f.name))
    print(f"已迁移生成照片到 {new_gen}")

    # Move features cache
    old_feat = data_dir / "xiaobu_features.txt"
    new_feat_dir = data_dir / "features"
    new_feat_dir.mkdir(parents=True, exist_ok=True)
    if old_feat.exists():
        shutil.move(str(old_feat), str(new_feat_dir / f"{user_id}_features.txt"))
        print(f"已迁移特征缓存到 {new_feat_dir / f'{user_id}_features.txt'}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("用法: python manage.py <command>")
        print("命令: init-owner")
        sys.exit(1)

    command = sys.argv[1]
    if command == "init-owner":
        cmd_init_owner()
    else:
        print(f"未知命令: {command}")
        sys.exit(1)
