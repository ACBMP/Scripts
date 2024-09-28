from util import *
import markdown as md

def add_post(title, post):
    db = connect()
    db.home.insert_one({"title": title, "content": md.markdown(post)})
    print("Done!")
    return


def remove_post(title, post):
    db = connect()
    db.home.delete_one({"title": title, "content": md.markdown(post)})
    print("Done!")
    return


if __name__ == "__main__":
    with open("post.md") as f:
        lines = f.read().split("\n")
        title = lines[0]
        post = "\n".join(lines[1:])
        remove_post(title, post)
        f.close()

