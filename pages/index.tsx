import { isEmpty } from "lodash"
import { useTranslation } from "next-i18next"
import { serverSideTranslations } from "next-i18next/serverSideTranslations"
import React from "react"

import { Comments } from "@/components/common/Comments"
import { Posts } from "@/components/common/Posts"
import Layout from "@/components/layout/Layout"
import Pagination from "@/components/layout/Pagination"
import Search from "@/components/layout/Search"
import { typesense } from "@/lib/typesenseClient"
import { PaginationType, PostType } from "@/types/blog"
import { PostSearchParams, PostSearchResponse } from "@/types/typesense"

export async function getServerSideProps(ctx) {
  const page = parseInt(ctx.query.page || 1)
  const query = ctx.query.query || ""
  const tags = ctx.query.tags || ""
  const language = ctx.query.language || ""
  const category = ctx.query.category || ""

  // if (language && language !== ctx.locale) {
  //   language = null
  // }
  let filterBy = `status:!=[pending]`
  if (process.env.VERCEL_ENV !== "production") {
    filterBy = `status:!=[obsolete]`
  }

  filterBy = !isEmpty(tags) ? filterBy + ` && tags:=[${tags}]` : filterBy
  filterBy = !isEmpty(language)
    ? filterBy + ` && language:[${language}]`
    : filterBy
  filterBy = !isEmpty(category)
    ? filterBy + ` && category:[${category}]`
    : filterBy

  const searchParameters: PostSearchParams = {
    q: query,
    query_by:
      "tags,title,doi,authors.name,authors.url,reference.url,abstract,summary,content_text",
    filter_by: filterBy,
    sort_by: ctx.query.query ? "_text_match:desc" : "published_at:desc",
    per_page: 10,
    page: page && page > 0 ? page : 1,
  }

  const data: PostSearchResponse = await typesense
    .collections("posts")
    .documents()
    .search(searchParameters)
  const posts = data.hits?.map((hit) => hit.document)
  const pages = Math.ceil(data.found / 10)
  const pagination = {
    base_url: "/posts",
    query: query,
    language: language,
    category: category,
    generator: "",
    tags: tags,
    page: page,
    pages: pages,
    total: data.found,
    prev: page > 1 ? page - 1 : null,
    next: page < pages ? page + 1 : null,
  }

  return {
    props: {
      ...(await serverSideTranslations(ctx.locale!, ["common"])),
      posts,
      pagination,
      locale: ctx.locale,
    },
  }
}

type Props = {
  posts: PostType[]
  pagination: PaginationType
  locale: string
}

const PostsPage: React.FunctionComponent<Props> = ({
  posts,
  pagination,
  locale,
}) => {
  const { t } = useTranslation("common")

  return (
    <>
      <Layout>
        <div className="mx-auto max-w-2xl sm:text-center">
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            {t("posts.title")}
          </h2>
        </div>
        <Search pagination={pagination} locale={locale} />
        <Pagination pagination={pagination} />
        <Posts posts={posts} pagination={pagination} />
        {pagination.total > 0 && <Pagination pagination={pagination} />}
        <div className="mx-auto max-w-2xl pb-5 lg:max-w-4xl">
          <Comments locale={locale} />
        </div>
      </Layout>
    </>
  )
}

export default PostsPage
