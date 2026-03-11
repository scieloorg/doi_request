import argparse
import sys

from doi_request.auth import hash_password
from doi_request.models import configure_session_engine, transactional_session
from doi_request.models.depositor import User


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Create or update a DOI Manager admin user.')
    parser.add_argument('--username', required=True, help='Username for the admin account')
    parser.add_argument('--password', required=True, help='Password for the admin account')
    parser.add_argument(
        '--activate',
        action='store_true',
        help='Force the user to be active when updating an existing account',
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    configure_session_engine()

    with transactional_session() as session:
        user = session.query(User).filter(User.username == args.username).first()
        if user is None:
            user = User(
                username=args.username,
                password_hash=hash_password(args.password),
                is_active=True,
                is_admin=True,
            )
            session.add(user)
            print('created user %s' % args.username)
            return 0

        user.password_hash = hash_password(args.password)
        user.is_admin = True
        if args.activate:
            user.is_active = True
        print('updated user %s' % args.username)
        return 0


if __name__ == '__main__':
    sys.exit(main())
